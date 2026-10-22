"""Exercise the real SMTP transport against a local, non-delivering test relay."""
import asyncio
import pytest
from app.notifications.email import EmailMessage, SmtpEmailSender


@pytest.mark.asyncio
async def test_smtp_transport_sends_a_complete_message_over_loopback():
    bodies = []

    async def relay(reader, writer):
        writer.write(b'220 localhost test relay\r\n')
        await writer.drain()
        try:
            while line := await reader.readline():
                command = line.decode().strip().upper()
                if command.startswith('EHLO') or command.startswith('HELO'):
                    writer.write(b'250 localhost\r\n')
                elif command.startswith('MAIL FROM:') or command.startswith('RCPT TO:'):
                    writer.write(b'250 OK\r\n')
                elif command == 'DATA':
                    writer.write(b'354 End with a dot\r\n')
                    await writer.drain()
                    data = []
                    while (part := await reader.readline()) != b'.\r\n':
                        if not part:
                            return
                        data.append(part)
                    bodies.append(b''.join(data))
                    writer.write(b'250 Accepted by local test relay\r\n')
                elif command == 'QUIT':
                    writer.write(b'221 Bye\r\n')
                    await writer.drain()
                    return
                else:
                    writer.write(b'250 OK\r\n')
                await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(relay, '127.0.0.1', 0)
    try:
        port = server.sockets[0].getsockname()[1]
        sender = SmtpEmailSender(host='127.0.0.1', port=port, sender='no-reply@example.com',
                                 use_starttls=False)
        await sender.send(EmailMessage(to=('resident@example.com',), subject='Maintenance update',
                                       body='A synthetic local transport acceptance message.'))
        assert len(bodies) == 1
        assert b'Subject: Maintenance update' in bodies[0]
        assert b'A synthetic local transport acceptance message.' in bodies[0]
    finally:
        server.close()
        await server.wait_closed()
