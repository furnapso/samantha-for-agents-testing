def generate_header(sampleRate, bitsPerSample, channels):
    # Some veeery big number here instead of: #samples * channels * bitsPerSample // 8
    datasize = 10240000
    # (4byte) Marks file as RIFF
    o = bytes("RIFF", 'ascii')
    # (4byte) File size in bytes excluding this and RIFF marker
    o += (datasize + 36).to_bytes(4, 'little')
    # (4byte) File type
    o += bytes("WAVE", 'ascii')
    # (4byte) Format Chunk Marker
    o += bytes("fmt ", 'ascii')
    # (4byte) Length of above format data
    o += (16).to_bytes(4, 'little')
    # (2byte) Format type (7 - MULAW)
    o += (7).to_bytes(2, 'little')
    # (2byte)
    o += (channels).to_bytes(2, 'little')
    # (4byte)
    o += (sampleRate).to_bytes(4, 'little')
    o += (sampleRate * channels * bitsPerSample //
            8).to_bytes(4, 'little')  # (4byte)
    o += (channels * bitsPerSample // 8).to_bytes(2,
                                                    'little')               # (2byte)
    # (2byte)
    o += (bitsPerSample).to_bytes(2, 'little')
    # (4byte) Data Chunk Marker
    o += bytes("data", 'ascii')
    # (4byte) Data size in bytes
    o += (datasize).to_bytes(4, 'little')
    return o
