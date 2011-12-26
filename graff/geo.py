import math

import geohash

def haversine_dist(lat1, lng1, lat2, lng2, radius=6.3781e6):
    """Get the distance between two points, in meters."""
    return 2 * radius * math.asin(
        math.sqrt(math.sin((lat2 - lat1) / 2.0) ** 2 +
                  math.cos(lat1) * math.cos(lat2) *
                  math.sin((lng2 - lng1) / 2.0) ** 2))

def get_bounding_geohash(n, w, s, e):
    """Get the bounding geohash for a given geobox. The geohash will be the
    smallest geohash that completely contains the given geobox (and will usually
    be quite a bit larger).
    """
    lat = 0.5 * (n + s)
    lng = 0.5 * (w + e)
    gh = geohash.encode(lat, lng)
    for x in xrange(12, 0, -1):
        hash_part = gh[:x]
        bbox = geohash.bbox(hash_part)
        if (bbox['n'] >= n and bbox['s'] <= s and bbox['w'] <= w and bbox['e'] >= e):
            return hash_part
    return ''
