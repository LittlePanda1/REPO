from time import time

RATE_LIMIT = {}
SEEN_MESSAGE_IDS = {}
MESSAGE_TTL = 10

def cleanup_seen_ids(now):
    for mid, ts in list(SEEN_MESSAGE_IDS.items()):
        if now - ts > MESSAGE_TTL:
            del SEEN_MESSAGE_IDS[mid]
