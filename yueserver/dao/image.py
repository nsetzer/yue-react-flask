from PIL import Image, ImageOps
import io

class ImageScale(object):

    XXSMALL = 1
    XSMALL  = 2
    SMALL   = 3
    MEDIUM  = 4
    LARGE   = 5
    XLARGE  = 6
    LANDSCAPE_XSMALL  = 7
    LANDSCAPE_SMALL  = 8
    LANDSCAPE_MEDIUM = 9
    LANDSCAPE_LARGE  = 10
    LANDSCAPE_XLARGE  = 11
    THUMB  = 12

    _scales = [
        ("unknown", (0, 0)),
        ("xxsmall", (32, 32)),
        ("xsmall", (64, 64)),
        ("small", (128, 128)),
        ("medium", (256, 256)),
        ("large", (512, 512)),
        ("xlarge", (1024, 1024)),
        ("landscape_xsmall", (64, 36)),
        ("landscape_small", (128, 72)),
        ("landscape_medium", (256, 144)),
        ("landscape_large", (512, 288)),
        ("landscape_xlarge", (1024, 576)),
        ("thumb", (80, 60)),
    ]

    @staticmethod
    def size(scale):
        return ImageScale._scales[scale][1]

    @staticmethod
    def name(scale):
        return ImageScale._scales[scale][0]

    @staticmethod
    def names():
        return [scale[0] for scale in ImageScale._scales]

    @staticmethod
    def fromName(name):
        for i, (n, _) in enumerate(ImageScale._scales):
            if name == n:
                return i
        return 0

def scale_image_stream(inputStream, outputStream, scale):

    img = Image.open(inputStream)
    img.load()

    # prevents an error in expand below
    # convert the pixel format so that the fill argument makes sense
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    width, height = img.size

    tgt_width, tgt_height = ImageScale.size(scale)

    # TODO: scale and crop one dim
    # this may depend on square and landscape shape
    if height < width:
        scale = (tgt_height / float(height))
        wsize = int(scale * width)
        hsize = tgt_height
    else:
        scale = (tgt_width / float(width))
        wsize = tgt_width
        hsize = int(scale * height)

    img = img.resize((wsize, hsize), Image.BILINEAR)

    if img.size[1] < tgt_height:
        # pad with transparent pixels on the top and bottom
        d = tgt_height - img.size[1]
        padding = (0, int(d / 2), 0, round(d / 2))
        img = ImageOps.expand(img, padding, fill=(0, 0, 0, 255))
    elif img.size[0] < tgt_width:
        # pad with transparent pixels on the left and right
        d = tgt_width - img.size[0]
        padding = (int(d / 2), 0, round(d / 2), 0)
        img = ImageOps.expand(img, padding, fill=(0, 0, 0, 255))
    elif img.size[1] > tgt_height or img.size[0] > tgt_width:
        # crop the image, centered
        img = ImageOps.fit(img, (tgt_width, tgt_height))

    # the current FileSystem framework does not support seek()
    # img.save requires a seekable file object, and as the only
    # use case at present, this is a workaround until other use
    # cases are determined.

    nBytes = 0
    with io.BytesIO() as bImg:
        img.save(bImg, format="png")
        bImg.seek(0)
        for dat in iter(lambda: bImg.read(2048), b""):
            nBytes += len(dat)
            outputStream.write(dat)

    return img.size[0], img.size[1], nBytes

def scale_image_file(fs, src_path, tgt_path, scale):

    with fs.open(src_path, "rb") as rb:
        with fs.open(tgt_path, "wb") as wb:
            return scale_image_stream(rb, wb, scale)
