import os
import io
import logging
import shutil
import mimetypes

from six.moves import urllib

from django.template import Template, Context
from cactus.compat.paths import PageCompatibilityLayer
from cactus.utils.url import ResourceURLHelperMixin
from cactus.utils.helpers import memoize

logger = logging.getLogger(__name__)


class WebContent(PageCompatibilityLayer, ResourceURLHelperMixin):

    def __init__(self, site, source_path):
        self.site = site
        self.source_path = source_path
        # The URL where this element should be linked in "base" pages
        self.link_url = '/{0}'.format(self.source_path)

    def __repr__(self):
        return '<{0}: {1}>'.format(self.__class__.__name__, self.source_path)

    @staticmethod
    def fromPath(path, site):
        mime, encoding = mimetypes.guess_type(path)
        if mime and mime.startswith('image'):
            logger.warning("Image in /pages directory found: %s", path)
            return PageImage(site, path)
        return Page(site, path)

    def is_html(self):
        return self._path.endswith('.html')

    def is_index(self):
        return self._path.endswith('index.html')

    @property
    def _path(self):
        return urllib.parse.urlparse(self.source_path).path

    @property
    def absolute_final_url(self):
        """
        Return the absolute URL for this page in the final build
        """
        return urllib.parse.urljoin(self.site.url, self.final_url)

    @property
    def full_source_path(self):
        return os.path.join(self.site.path, 'pages', self.source_path)

    @property
    def full_build_path(self):
        return os.path.join(self.site.build_path, self.build_path)

    def build(self):
        """
        The build method needs to be implemented by the subclass of WebContent
        """
        raise NotImplementedError('build() must be implemented by subclass')


class PageImage(WebContent):

    def __init__(self, site, source_path):
        super(PageImage, self).__init__(site, source_path)
        self.final_url = self.link_url
        self.build_path = self.source_path

    def is_html(self):
        return False

    def build(self):
        """
        Copy the page image to the output folder.
        """
        try:
            os.makedirs(os.path.dirname(self.full_build_path))
        except OSError:
            pass

        shutil.copy(self.full_source_path, self.full_build_path)


class Page(WebContent):

    def __init__(self, site, source_path):
        super(Page, self).__init__(site, source_path)
        self._render_cache = None
        self.discarded = False

        if self.site.prettify_urls:
            # The URL where this element should be linked in "built" pages
            if self.is_html():
                if self.is_index():
                    self.final_url = self.link_url.rsplit('index.html', 1)[0]
                else:
                    self.final_url = '{0}/'.format(self.link_url.rsplit('.html', 1)[0])
            else:
                self.final_url = self.link_url

            # The path where this element should be built to
            if not self.is_html() or self.source_path.endswith('index.html'):
                self.build_path = self.source_path
            else:
                self.build_path = '{0}/{1}'.format(self.source_path.rsplit('.html', 1)[0], 'index.html')
        else:
            self.final_url = self.link_url
            self.build_path = self.source_path

    def data(self):
        with io.FileIO(self.full_source_path, 'r') as f:
            try:
                return f.read().decode('utf-8')
            except:
                logger.warning("Template engine could not process page: %s", self.path, exc_info=True)
                return u""

    def context(self, data=None, extra=None):
        """
        The page context.
        """
        if extra is None:
            extra = {}

        context = {'__CACTUS_CURRENT_PAGE__': self,}

        page_context, data = self.parse_context(data or self.data())

        context.update(self.site.context())
        context.update(extra)
        context.update(page_context)

        return Context(context)

    def clear_cache(self):
        self._render_cache = None

    def render(self):
        if not self._render_cache:
            self._render_cache = self._render()
        return self._render_cache

    def _render(self):
        """
        Takes the template data with context and renders it to the final output file.
        """

        data = self.data()
        context = self.context(data=data)

        # This is not very nice, but we already used the header context in the
        # page context, so we don't need it anymore.
        page_context, data = self.parse_context(data)

        context, data = self.site.plugin_manager.preBuildPage(
            self.site, self, context, data)

        return Template(data).render(context)

    def build(self):
        """
        Save the rendered output to the output file.
        """
        # TODO: Fix inconsistency w/ static
        logger.debug('Building {0} --> {1}'.format(self.source_path, self.final_url))
        # TODO: This calls preBuild indirectly. Not great.
        data = self.render()

        if not self.discarded:

            # Make sure a folder for the output path exists
            try:
                os.makedirs(os.path.dirname(self.full_build_path))
            except OSError:
                pass

            with io.FileIO(self.full_build_path, 'w') as f:
                f.write(data.encode('utf-8'))

            self.site.plugin_manager.postBuildPage(self)

    def parse_context(self, data, splitChar=':'):
        """
        Values like

        name: koen
        age: 29

        will be converted in a dict: {'name': 'koen', 'age': '29'}
        """

        if not self.is_html():
            return {}, data

        values = {}
        lines = data.splitlines()
        if not lines:
            return {}, ''

        for i, line in enumerate(lines):

            if not line:
                continue

            elif splitChar in line:
                line = line.split(splitChar)
                values[line[0].strip()] = (splitChar.join(line[1:])).strip()

            else:
                break

        return values, '\n'.join(lines[i:])
