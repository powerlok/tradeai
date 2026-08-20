import httpx
import socket


def test_rest():
    try:
        r = httpx.get('https://api.binance.com/api/v3/time', timeout=5)
        print('REST', r.status_code)
    except Exception as e:
        print('REST_FAILED', repr(e))


def test_tcp():
    try:
        s = socket.socket()
        s.settimeout(5)
        s.connect(('stream.binance.com', 9443))
        s.close()
        print('TCP ok')
    except Exception as e:
        print('TCP_FAILED', repr(e))


if __name__ == '__main__':
    test_rest()
    test_tcp()
