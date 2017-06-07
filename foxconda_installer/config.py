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
        self.clear()

    def clear(self):
        self.entries = {}

    def getEntry(self, k):
        return self.entries.get(k, None)

    def setEntry(self, k, v):
        self.entries[k] = v

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
                    # all of the sudden, the Darwin installer complained
                    # that it wasn't provided a Windows icon???
                    #return v
                    return _icon['win']
                    break
        return None

    def read(self, fname = None):
        '''
        Reads the configuration file and adds and updates the entries to
        this.
        :param fname:   file name (if not specified, self.config is used)
        '''
        if fname is None:
            fname = self.config
        with open(fname) as f:
            self.entries = yaml.load(f.read())

    def write(self, fname = None):
        if fname is None:
            fname = self.config
        with open(fname, 'w') as f:
            f.write(yaml.dump(self.entries))


if __name__ == '__main__':
    pass

