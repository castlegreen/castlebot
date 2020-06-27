
import os
import email
import poplib
import slack

def checkMail():
    pop = poplib.POP3_SSL('pop.gmail.com')
    pop_user = os.environ['CASTLEBOT_POP_USER']
    pop.user(pop_user)
    pop.pass_(os.environ['CASTLEBOT_POP_PASS'])
    n = len(pop.list()[1])

    print(n, 'messages')
    print()

    for i in range(n):
        print('@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ message', i+1)
        lines = pop.retr(i+1)[1]
        #for j in lines:
        #    print(j)
        raw_email = b'\n'.join(lines)
        msg = email.message_from_bytes(raw_email)

        if False:
            print(type(msg))
            #print(msg.keys())
            print('To:', msg['To'])
            print('From:', msg['From'])
            print('Subject:', msg['Subject'])
            print('is_multipart:', msg.is_multipart())
            print(type(msg.get_payload()))

        interesting = ('events@castlegreen.com' in msg['From'] or
                       'Aaron@castlegreen.com' in msg['From'] or
                       'FrontDesk@castlegreen.com' in msg['From'] or
                       pop_user in msg['From'])
        if not interesting:
            print('@@@@ SKIPPING From:', msg['From'])
            print('@@@@          Subject:', msg['Subject'])
            continue
        #for part in msg.walk():
        #    print(part.get_content_type())
        body = ''
        attachments = []
        multipart = ('multipart/alternative', 'multipart/related')
        if msg.is_multipart():
            for part in msg.get_payload():
                print(type(part), part.get_content_type())
                disp = part.get('Content-Disposition', '')
                ct = part.get_content_type()
                print('@@@@ ct:', ct)
                if ct in multipart:
                    for subpart in part.walk():
                        print('    subpart:', type(subpart), part.get_content_type())
                        if part.get_content_type() in multipart:
                            for sp in subpart.walk():
                                print('        subsubpart:', type(sp), sp.get_content_type())
                                if sp.get_content_type() == 'text/plain':
                                    newBody = sp.get_payload(decode=True)
                                    newBody = newBody.decode('utf-8')
                                    print('@@@ got body') #x, newBody)
                                    body += newBody
                                    #msgNo = i+1
                elif 'attachment' in disp:
                    print('    disp:', repr(disp))
                    ct = part.get_content_type()
                    print('    content:', ct)
                    if True: #('pdf' in ct) or ('office' in ct):
                        attachment = part.get_payload(decode=True)
                        filename = extractFilename(disp)
                        attachments.append((filename, attachment))
                elif ct == 'text/plain':
                    newBody = part.get_payload(decode=True)
                    newBody = newBody.decode('utf-8')
                    print('@@@ got toplevel body') #x, newBody)
                    body += newBody
                    
                    
        else:
            print('@@@ got simple body')
            body = msg.get_payload()

        if body:
            body = parseBody(body)
            if body:
                client = postToSlack(body)
                uploadAttachments(client, attachments)
        print()

    msgNo = None
    if msgNo:
        print('deleting', msgNo)
        print(pop.dele(msgNo))
        print()
    
    # Upon receiving this quit command, Gmail "deletes" any messages
    # we've read...  regardless of any delete commands, and regardless
    # of the POP3 settings in Gmail.
    print(pop.quit())
    
    return


def parseBody(body):
    lines = body.splitlines()
    #print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ lines", len(lines))
    newBody = []
    skipHeaders = False
    skipBlanks = False
    for i, line in enumerate(lines):
        #print(i, '@@@:', repr(line))
        if 'Forwarded message' in line:
            skipHeaders = True
            continue
        if skipHeaders:
            if line:
                continue
            skipHeaders = False
            skipBlanks = True
            continue
        if skipBlanks:
            if not line:
                continue
            skipBlanks = False
            #print('@@@@ message starts here')
        if 'Best regards' in line:
            break
        newBody.append(line)
    #print()
    return '\n'.join(newBody)


def connectToSlack():
    return slack.WebClient(token=os.environ['SLACK_API_TOKEN'])


def postToSlack(text):
    client = connectToSlack()
    print("@@@@ POST") #, text)
    response = client.chat_postMessage(
        #username='sparklebot',
        as_user=True,
        channel='#events',
        #channel='#dev',
        text=text)
    assert response["ok"]
    return client


def extractFilename(contentHeader):
    filename = 'unknown'
    print('@@@@@@@@@@@ header', contentHeader)
    quote = contentHeader.find('"')
    if quote >= 0:
        cquote = contentHeader.rfind('"')
        filename = contentHeader[quote+1:cquote]
        print('@@@@@@@@@@@ filename', filename)
    return filename

def uploadAttachments(client, attachments):
    for filename, attachment in attachments:
        uploadAttachment(client, filename, attachment)

def uploadAttachment(client, filename, attachment):
    stream = open(filename, 'wb')
    stream.write(attachment)
    stream.close()
    response = client.files_upload(
        #channels='#dev',
        channels='#events',
        title=filename,
        file=filename)
    assert response["ok"]


def crash():
    assert False

def main():
    #crash()
    checkMail()

def _main():
    import traceback
    try:
        main()
    except:
        filename = 'crash.txt'
        stream = open(filename, 'w')
        traceback.print_exc(file=stream)
        stream.close()
        client = connectToSlack()
        response = client.files_upload(
            channels='#dev',
            title=filename,
            file=filename)
        assert response["ok"]

_main()
#main()
