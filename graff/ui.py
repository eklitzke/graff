"""UIModules"""

import re
import tornado.web

module_suffix = re.compile('Module$')

class UIModule(tornado.web.UIModule):

    def render_string(self, tmpl, **kwargs):
        return super(UIModule, self).render_string('../modules/' + tmpl, **kwargs)

class PhotoUploadModule(UIModule):

    def render(self):
        return self.render_string('photo_upload.html')

class RecentPhotosModule(UIModule):

    def render(self, recent_photos, esc, do_map):
        return self.render_string('recent_photos.html', recent_photos=recent_photos, esc=esc, do_map=do_map)

class AboutModule(UIModule):

    def render(self):
        return self.render_string('about.html')

modules = {}
for v in globals().values():
    try:
        if issubclass(v, tornado.web.UIModule):
            modules[module_suffix.sub('', v.__name__)] = v
    except TypeError:
        pass
del modules['UI']
