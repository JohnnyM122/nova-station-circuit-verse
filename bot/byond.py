import asyncio
import struct
import json
import urllib.parse
import logging

logger = logging.getLogger("CVNovaHelper.byond")

class ByondClient:
    def __init__(self, host='127.0.0.1', port=7777, comms_key=None):
        self.host = host
        self.port = port
        self.comms_key = comms_key

    async def query(self, query_str: str, timeout=5.0):
        if not query_str.startswith('?'):
            query_str = '?' + query_str
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=timeout
            )
            qbytes = query_str.encode('latin1')
            packet = b'\x00\x83' + struct.pack('>H', len(qbytes) + 6) + b'\x00\x00\x00\x00\x00' + qbytes + b'\x00'
            writer.write(packet)
            await writer.drain()

            resp = await asyncio.wait_for(reader.read(65536), timeout=timeout)
            writer.close()
            await writer.wait_closed()

            if len(resp) >= 5 and resp[:2] == b'\x00\x83':
                resp_type = resp[4]
                if resp_type == 0x06: # String
                    data = resp[5:-1].decode('latin1', errors='replace')
                    try:
                        return json.loads(data)
                    except Exception:
                        return data
                elif resp_type == 0x2a: # Float
                    return struct.unpack('<f', resp[5:9])[0]
            return resp
        except Exception as e:
            return None

    async def get_status(self):
        return await self.query(f'?status&key={self.comms_key}')

    async def get_manifest(self):
        return await self.query('?manifest')

    async def get_players(self):
        res = await self.query('?playerlist')
        if res is not None and isinstance(res, list):
            return res
        return await self.query('?players')

    async def get_adminwho(self):
        return await self.query(f'?adminwho&key={self.comms_key}')

    async def handle_ticket(self, action, ticket_id=None, system='admin', sender='Discord Staff', msg=None):
        params = {
            'ticket': '1',
            'key': self.comms_key,
            'action': action,
            'system': system,
            'sender': sender
        }
        if ticket_id is not None:
            params['id'] = str(ticket_id)
        if msg is not None:
            params['msg'] = msg
        query_str = urllib.parse.urlencode(params)
        return await self.query('?' + query_str)

    async def issue_ban(self, ckey, bantype='TEMPBAN', duration=0, reason='Banned via Discord', sender='Discord Staff', job=None):
        params = {
            'ban': '1',
            'key': self.comms_key,
            'ckey': ckey,
            'bantype': bantype,
            'duration': str(duration),
            'reason': reason,
            'sender': sender
        }
        if job:
            params['job'] = job
        query_str = urllib.parse.urlencode(params)
        return await self.query('?' + query_str)

    async def kick_player(self, ckey, reason='Kicked by server administration', sender='Discord Staff'):
        params = {
            'control': '1',
            'key': self.comms_key,
            'action': 'kick',
            'ckey': ckey,
            'reason': reason,
            'sender': sender
        }
        query_str = urllib.parse.urlencode(params)
        return await self.query('?' + query_str)

    async def send_announcement(self, msg, sender='Discord Staff'):
        params = {
            'control': '1',
            'key': self.comms_key,
            'action': 'announce',
            'msg': msg,
            'sender': sender
        }
        query_str = urllib.parse.urlencode(params)
        return await self.query('?' + query_str)

    async def reload_admins(self, sender='Discord Staff'):
        params = {
            'control': '1',
            'key': self.comms_key,
            'action': 'reload_admins',
            'sender': sender
        }
        query_str = urllib.parse.urlencode(params)
        return await self.query('?' + query_str)

    async def reload_access_flags(self, sender='Discord Staff'):
        params = {
            'control': '1',
            'key': self.comms_key,
            'action': 'reload_access_flags',
            'sender': sender
        }
        query_str = urllib.parse.urlencode(params)
        return await self.query('?' + query_str)

    async def remote_reboot(self, sender='Discord Staff'):
        params = {
            'control': '1',
            'key': self.comms_key,
            'action': 'reboot',
            'sender': sender
        }
        query_str = urllib.parse.urlencode(params)
        return await self.query('?' + query_str)
