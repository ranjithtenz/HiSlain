import os
import imp
import sys

from datetime import datetime
from dateutil import parser

from jinja2 import Environment, FileSystemLoader
import yaml

import utils
from hooks import Hooker

post_meta_defaults = {
#        meta name  : (type, default value)
        'published' : (datetime, lambda p, s: datetime.now()),
        'permalink' : (unicode, lambda p, s: utils.slugify(p.title) + '.html'),
        'tags'      : (list, []),
        }

def _parsetype(type, data):
    if type is datetime:
        return parser.parse(data)
    elif type is unicode:
        return unicode(data, encoding='UTF-8')
    elif type is list:
        return [i.strip() for i in data.split(',')]
    else:
        return data

def _dumptype(type, data):
    if type is datetime:
        return data.isoformat()
    elif type is list:
        return ', '.join(data)
    else:
        return data

class Block():
    def __init__(self, file_path=None, blog=None, default_meta=True):
        self.meta = {}
        self.title = ""
        self.content = ""
        self.blog = blog
        if file_path:            
            self.source_path = file_path

            file = open(file_path, 'r')
            self.title = file.readline().rstrip()

            l = file.readline()
            
            while l != "\n":
                l = l.rstrip()
                meta = l.split(":")
                key = meta[0]
                value = ":".join(meta[1:]).lstrip()
                self.meta[key] = value
                l = file.readline()

            self.content = file.read().rstrip()
            if default_meta:
                # Set in default values, and parse according to type, if default_meta is set
                for k, v in post_meta_defaults.items():
                    if k in self.meta:
                        self.meta[k] = _parsetype(v[0], self.meta[k])
                    else:
                        if callable(v[1]):
                            self.meta[k] = v[1](self, self.blog.settings)
                        else:
                            self.meta[k] = v[1]

    def render_html(self):
        if not hasattr(self, 'content_html'):
            try:
                self.content_html = self.blog.hooks.as_string("render", self)
            except KeyError:
                print "No renderer plugin found!"
                sys.exit(-1)
            
        return self.content_html

    def save(self):
        self.to_file(file(self.source_path, 'w'))

    def to_file(self, file):
        file.write(self.title + '\n')
        
        for k, v in self.meta.items():
            if k in post_meta_defaults:
                v = _dumptype(post_meta_defaults[k][0], v)
                file.write(("%s: %s" % (k, v)) + '\n')

        file.write('\n')

        file.write(self.content)

class Blog():
    def __init__(self, dir):
        self.settings = read_config(file(os.path.join(dir, "blog.yaml")))
        posts_dir = os.path.join(dir, self.settings.get("postspath", "posts"))
        self.posts = [
            Block(os.path.join(posts_dir,post_file), blog=self) 
            for post_file in os.listdir(posts_dir) 
            if post_file.endswith('.post')
            ]

        pages_dir = os.path.join(dir, self.settings.get("pagespath", "pages"))
        self.pages = [
            Block(os.path.join(pages_dir, page_file), blog=self) 
            for page_file in os.listdir(pages_dir)
            if page_file.endswith('.page')
            ]

        themes_path = os.path.join(dir, self.settings.get("themespath","themes"))

        templates_path = os.path.join(themes_path, self.settings.get("theme", "simpl"))
        self.env = Environment(loader=FileSystemLoader(templates_path))
        self.settings['theme_path'] = templates_path            
        self.settings['out_path'] = os.path.join(dir, self.settings.get('out', 'out'))
        self.settings['media_path'] = os.path.join(dir, self.settings.get('media', 'media'))
        self.settings['blog_dir'] = dir

        self.hooks = Hooker()
        plugins_path = os.path.join(dir, self.settings.get("pluginspath","plugins"))
       
        for plugin_file in os.listdir(plugins_path):
            if plugin_file.endswith('.py'):
                plugin = imp.load_source(os.path.basename(plugin_file).split('.')[0], os.path.join(plugins_path,plugin_file))
                plugin.main(self)
       
                    
def read_config(file):
    return yaml.load(file)


