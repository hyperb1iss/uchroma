#
# Calculate the checksum for a report buffer
#
# We do this in C because this function is invoked for
# every single buffer and accounts for a large percentage
# of total CPU time when running an animation.
#
def fast_crc(char *buf):
    cdef unsigned int i
    cdef unsigned char crc = 0
    for i in range(1, 87):
        crc ^= buf[i]
    return crc
