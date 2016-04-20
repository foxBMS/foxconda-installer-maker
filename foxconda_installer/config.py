"""
:since:     Mon Apr 18 14:28:09 CEST 2016
:author:    Tim Fuehner <tim.fuehner@iisb.fraunhofer.de>
$Id$
"""

import sys
import yaml
import os

class InstallerConfig(object):

    def __init__(self, config = 'installer.yaml'):
        self.config = config
        self.dirname = os.path.dirname(config)
        self.entries = None

    def getEntry(self, k):
        return self.entries.get(k, None)

    def getFiles(self, k):
        if k in ['license', 'data']:
            return self.getTopicFiles(k, 'files')
        if k == 'postinstall':
            return self.getTopicFiles('postinstall', 'scripts')
        if k == 'icon':
            _icon = self.getIconFile()
            if _icon:
                return [_icon]
            else:
                return []
        if k == 'payload':
            return [self.entries['payload']['file']]
        _f = self.getEntry(k)
        if _f: return [_f]
        return []

    def getAllFiles(self):
        _f = []
        for k in ['icon', 'image', 'payload', 'license', 'postinstall', 'data']:
            _f += self.getFiles(k)
        return _f

    def getTopicFiles(self, key, subkey):
        _lic = self.entries.get(key, None)
        if not _lic: return []
        _lic = _lic.get(subkey, None)
        if not _lic: return []
        return _lic

    def getIconFile(self):
        _icon = self.entries.get('icon', None)
        if _icon:
            for k,v in _icon.iteritems():
                if sys.platform.startswith(k):
                    return v
                    break
                elif k == 'osx' and sys.platform.startswith('darwin'):
                    return v
                    break
        return None

    def read(self):
        with open(self.config) as f:
            self.entries = yaml.load(f.read())


if __name__ == '__main__':
    pass
