import os
from IPython.display import display, HTML
from PIL import Image
import numpy as np
from csxtools.utils import get_fastccd_images


def _make_link(filepath, filename):
    html = '<a href="/{}/{}" target="_blank">'.format(filepath, filename)
    html += 'Click to download {} ........</a>'.format(filename)
    return html


def _make_tiff_image(image, filename):
    im = Image.fromarray(np.asarray(image))
    im.save(filename)


def make_tiff_links(stack, prefix='image_', tempdir='tmp'):
    """Make tiff images into temp directory and return links

    This function makes tiff images of the image stack

    """

    if (stack.ndim > 3) or (stack.ndim < 2):
        raise ValueError("Image array must be of either 2 or 3 dimensions")

    td = os.environ.get('HOME')
    if td is None:
        raise RuntimeError("Unable to determine home directory for temp "
                            "files.")

    user = os.environ.get('USER')
    if user is None:
        raise RuntimeError("Unable to determine username")

    td = os.path.join(td, tempdir)

    if stack.ndim == 2:
        stack = [stack]

    html = ''
    for n, s in enumerate(stack):
        filename = '{}{}.tiff'.format(prefix,n)
        _make_tiff_image(s, os.path.join(td, filename))
        p = tempdir.split(os.pathsep)
        html += _make_link('/'.join(['user', user, 'view'] + p), filename)
        html += '<br>'

    return display(HTML(html))
