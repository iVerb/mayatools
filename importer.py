from __future__ import absolute_import

import os
import re

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from maya import cmds, mel

from ks.core.scene_name.core import SceneName
from sgfs import SGFS


sgfs = SGFS()


def comparison_name(name):
    name = name.rsplit('|', 1)[-1]
    name = name.rsplit(':', 1)[-1]
    if name.lower().endswith('deformed'):
        name = name[:-len('deformed')]
    return name


class ComboBox(QtGui.QComboBox):
    
    def itemData(self, index):
        data = super(ComboBox, self).itemData(index).toPyObject()
        return self._conform_item_data(data)
    
    def _conform_item_data(self, data):
        if isinstance(data, QtCore.QString):
            return str(data)
        if isinstance(data, dict):
            return dict((self._conform_item_data(k), self._conform_item_data(v)) for k, v in data.iteritems())
        return data
    
    def currentData(self):
        index = self.currentIndex()
        return self.itemData(index)
    
    def indexWithText(self, text):
        for i in xrange(self.count()):
            if self.itemText(i) == text:
                return i
    
    def selectWithText(self, text):
        index = self.indexWithText(text)
        if index is not None:
            self.setCurrentIndex(index)
            return True
    
    def indexWithData(self, key, value):
        for i in xrange(self.count()):
            data = self.itemData(i)
            if data and data.get(key) == value:
                return i
    
    def selectWithData(self, key, value):
        index = self.indexWithData(key, value)
        if index is not None:
            self.setCurrentIndex(index)
            return True


class Labeled(QtGui.QVBoxLayout):

    def __init__(self, label, widget):
        super(Labeled, self).__init__()
        self._label = QtGui.QLabel(label)
        self.addWidget(self._label)
        self._widget = widget
        self.addWidget(widget)
    
    def setVisible(self, visible):
        self._label.setVisible(visible)
        self._widget.setVisible(visible)


class Geometry(QtGui.QWidget):

    def __init__(self):
        super(Geometry, self).__init__()
        self.setLayout(QtGui.QHBoxLayout())
        self._setup_ui()

    def _setup_ui(self):
        
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.setContentsMargins(0, 0, 0, 0)
        
        icon = QtGui.QIcon('/home/mboers/Documents/icons/silk/icons/delete.png')
        icon = QtGui.QIcon(icon.pixmap(12, 12))
        self._delete_button = QtGui.QPushButton(icon, "Delete")
        self._delete_button.clicked.connect(self._on_delete)
        self._delete_button.setFixedSize(QtCore.QSize(70, 22))
        self.layout().addWidget(self._delete_button)
    
    def _on_delete(self):
        self.hide()
        self.destroy()

class RefDelegate(QtGui.QItemDelegate):
    
    def paint(self, painter, option, index):
        print 'paint', index.row()
        super(RefDelegate, self).paint(painter, option, index)


class Reference(Geometry):
    
    def __init__(self, reference=None):
        super(Reference, self).__init__()
        if reference is not None:
            self.setReference(reference)
    
    def _setup_ui(self):
        
        self._combobox = ComboBox()
        self._combobox.setItemDelegate(RefDelegate())
        self._populate_combobox()
        self.layout().addWidget(self._combobox)
        
        super(Reference, self)._setup_ui()
        
    
    def setReference(self, reference):
        self._combobox.selectWithData('reference', reference) or self._combobox.addItem(reference)
    
    def _populate_combobox(self):
        for reference in cmds.file(q=True, reference=True) or []:
            namespace = cmds.referenceQuery(reference, namespace=True).strip(':')
            icon = QtGui.QIcon('''
                /home/mboers/Documents/icons/silk/icons/error.png
                /home/mboers/Documents/icons/silk/icons/accept.png
                /home/mboers/Documents/icons/silk/icons/delete.png
            '''.strip().split()[self._combobox.count() % 3])
            icon = QtGui.QIcon(icon.pixmap(10, 10))
            self._combobox.addItem(icon, '%s: %s' % (namespace, os.path.basename(reference)), dict(
                namespace=namespace,
                reference=reference,
            ))
            #raw_nodes = cmds.referenceQuery(reference, nodes=True)


class Selection(Geometry):
    
    def __init__(self, selection=None):
        super(Selection, self).__init__()
        self.setSelection(selection)
    
    def _setup_ui(self):
                
        self._field = QtGui.QLineEdit()
        self.layout().addWidget(self._field)
        
        self._update_button = QtGui.QPushButton("Update")
        self._update_button.clicked.connect(self._on_update)
        self._update_button.setFixedSize(QtCore.QSize(60, 22))
        self.layout().addWidget(self._update_button)
        
        super(Selection, self)._setup_ui()
    
    def setSelection(self, selection):
        self._field.setText(', '.join(selection or []))
    
    def _on_update(self):
        selection = cmds.ls(sl=True)
        selection = [x for x in selection if cmds.nodeType(x) in ('mesh', 'transform')]
        self.setSelection(selection)


class Geocache(QtGui.QGroupBox):
    
    def __init__(self):
        super(Geocache, self).__init__()
        self._mapping = {}
        self._setup_ui()
    
    def _setup_ui(self):
        
        # Lots of layouts...
        self.setLayout(QtGui.QVBoxLayout())
        
        ## Cache widgets

        self._cache_layout = QtGui.QHBoxLayout()
        self.layout().addLayout(self._cache_layout)
        
        self._entity_combo = ComboBox()
        self._populate_entity_combo()        
        self._entity_combo.activated.connect(self._on_entity_changed)
        self._entity_pair = Labeled("Entity", self._entity_combo)
        self._cache_layout.addLayout(self._entity_pair)
            
        self._step_combo = ComboBox()
        self._step_combo.activated.connect(self._on_step_changed)
        self._step_pair = Labeled("Step", self._step_combo)
        self._cache_layout.addLayout(self._step_pair)
        
        self._cache_combo = ComboBox()
        self._cache_combo.activated.connect(self._on_cache_changed)
        self._cache_pair = Labeled("Cache", self._cache_combo)
        self._cache_layout.addLayout(self._cache_pair)
        
        self._object_combo = ComboBox()
        self._object_combo.activated.connect(self._on_object_changed)
        self._object_pair = Labeled("Object", self._object_combo)
        self._cache_layout.addLayout(self._object_pair)
        
        self._cache_field = QtGui.QLineEdit()
        # self._cache_field.editingFinished.connect(self._populate_reference_combo)
        self._cache_field_pair = Labeled("Path to Custom Geocache", self._cache_field)
        self._cache_layout.addLayout(self._cache_field_pair)
        
        self._cache_browse_button = QtGui.QPushButton("Browse")
        self._cache_browse_button.setMaximumSize(QtCore.QSize(50, 20))
        self._cache_browse_button.clicked.connect(self._on_cache_browse)
        self._cache_browse_button_pair = Labeled("", self._cache_browse_button)
        self._cache_layout.addLayout(self._cache_browse_button_pair)
        
        self._on_entity_changed()
        
        ## Geometry widgets
        
        self.layout().addWidget(QtGui.QLabel("Geometry & References"))
        
        self._geometry_layout = QtGui.QVBoxLayout()
        self.layout().addLayout(self._geometry_layout)
        
        button_layout = QtGui.QHBoxLayout()
        self.layout().addLayout(button_layout)
        
        icon = QtGui.QIcon('/home/mboers/Documents/icons/silk/icons/link_add.png')
        icon = QtGui.QIcon(icon.pixmap(12, 12))
        self._link_reference_button = QtGui.QPushButton(icon, "Add Reference Link")
        self._link_reference_button.clicked.connect(self._on_link_reference)
        self._link_reference_button.setMaximumHeight(22)
        button_layout.addWidget(self._link_reference_button)
        
        icon = QtGui.QIcon('/home/mboers/Documents/icons/silk/icons/link_add.png')
        icon = QtGui.QIcon(icon.pixmap(12, 12))
        self._link_selection_button = QtGui.QPushButton(icon, "Add Selection Link")
        self._link_selection_button.clicked.connect(self._on_link_selection)
        self._link_selection_button.setMaximumHeight(22)
        button_layout.addWidget(self._link_selection_button)
        
        icon = QtGui.QIcon('/home/mboers/Documents/icons/silk/icons/cog.png')
        icon = QtGui.QIcon(icon.pixmap(12, 12))
        self._edit_button = QtGui.QPushButton(icon, "Edit Mapping")
        self._edit_button.setMaximumHeight(22)
        button_layout.addWidget(self._edit_button)
        
        button_layout.addStretch()
        
    def _on_link_reference(self):
        box = Reference()
        self._geometry_layout.addWidget(box)
    
    def _on_link_selection(self):
        box = Selection()
        box._on_update()
        self._geometry_layout.addWidget(box)
    
    def _populate_entity_combo(self):
        print '# _populate_entity_combo'
        
        self._entity_combo.clear()
        
        workspace = cmds.workspace(q=True, directory=True)
        tasks = sgfs.entities_from_path(workspace)
        if not tasks or tasks[0]['type'] != 'Task':
            cmds.warning('Workspace does not have any tasks; %r -> %r' % (workspace, tasks))
            self._entity_combo.addItem('Custom')
            return
        
        task = tasks[0]
        entity = task.parent()
        
        # Populate shot combo with all reuses that match the current workspace.
        if entity['type'] == 'Shot':
            entities = []
            seq = entity.parent()
            seq_path = sgfs.path_for_entity(seq)
            for shot_path, shot in sgfs.entities_in_directory(seq_path, "Shot", load_tags=None):
                if shot.fetch('code').startswith(entity.fetch('code')[:6]):
                    entities.append((
                        shot['code'], shot_path, shot
                    ))
        
        elif entity['type'] == 'Asset':
            entities.append((
                entity['code'], sgfs.path_for_entity(entity), entity
            ))
        
        else:
            cmds.warning('Cannot extract entities from %r' % entity)
        
        for name, path, entity in entities:
            self._entity_combo.addItem(name, dict(
                name=name,
                path=path,
                entity=entity
            ))
        self._entity_combo.addItem('Custom')
        
        
    def _populate_step_combo(self):
        print '# _populate_step_combo'
        
        self._step_combo.clear()
        
        data = self._entity_combo.currentData()
        if not data:
            return
        entity_paty, entity = data['path'], data['entity']
        
        for task_path, task in sgfs.entities_in_directory(entity_paty, 'Task', load_tags=None):
            self._step_combo.addItem(task['step']['code'], (task_path, task))
            if task['step']['code'].lower().startswith('anim'):
                self._step_combo.setCurrentIndex(self._step_combo.count() - 1)

    def _on_entity_changed(self, index=None):
        
        shot = self._entity_combo.currentData()
        is_custom = shot is None
        
        self._cache_field_pair.setVisible(is_custom)
        self._cache_browse_button_pair.setVisible(is_custom)
        
        self._step_pair.setVisible(not is_custom)
        self._cache_pair.setVisible(not is_custom)
        self._object_pair.setVisible(not is_custom)
        
        if is_custom:
            pass
            # self._populate_reference_combo()
        else:
            self._populate_step_combo()
            self._on_step_changed()
    
    def _on_step_changed(self, index=None):
        self._populate_cache_combo()
        
    def _populate_cache_combo(self):
        print '# _populate_cache_combo'
        
        self._cache_combo.clear()
        self._cache_combo.addItem('Select...')
        
        data = self._step_combo.currentData()
        if not data:
            return
        task_path, task = data
        
        for geo_cache_name in ('geocache', 'geo_cache', 'geoCache'):
            path = os.path.join(task_path, 'maya', 'data', geo_cache_name)
            if os.path.exists(path):
                for name in os.listdir(path):
                    self._cache_combo.addItem(name, dict(path=os.path.join(path, name), name=name))
        
        self._populate_object_combo()
    
    def _on_cache_changed(self, index=None):
        if self._cache_combo.itemText(0) == 'Select...':
            if index:
                self._cache_combo.removeItem(0)
            else:
                return
        self._populate_object_combo()
    
    def _populate_object_combo(self):
        print '# _populate_object_combo'
        
        previous = self._object_combo.currentData() or {}
        
        self._object_combo.clear()
        
        data = self._cache_combo.currentData()
        if not data:
            return
        path, name = data['path'], data['name']
        
        if os.path.exists(path):
            for name in os.listdir(path):
                obj_path = os.path.join(path, name)
                self._object_combo.addItem(name, dict(path=obj_path, name=name))
                if obj_path == previous.get('path'):
                    self._object_combo.setCurrentIndex(self._object_combo.count() - 1)
        
        current = self._object_combo.currentData()
        if not current:
            self._object_combo.setCurrentIndex(self._object_combo.count() - 1)
            current = self._object_combo.currentData() or {}
        if not previous.get('path') or previous.get('path') != current.get('path'):
            self._on_object_changed()
    
    def _on_object_changed(self, index=None):
        pass

    def _on_cache_browse(self):
        file_name = str(QtGui.QFileDialog.getOpenFileName(self, "Select Geocache", os.getcwd(), "Geocaches (*.xml)"))
        if not file_name:
            return

        workspace = cmds.workspace(q=True, directory=True)
        relative = os.path.relpath(file_name, workspace)
        if relative.startswith('.'):
            self._cache_field.setText(file_name)
        else:
            self._cache_field.setText(relative)
        
    def cachePath(self):
        
        workspace = cmds.workspace(q=True, directory=True)
        entity_data = self._entity_combo.currentData()
                
        if not entity_data:
            relative = str(self._cache_field.text())
            if not relative:
                return
            path = os.path.join(workspace, relative)
        
        else:
            data = self._object_combo.currentData()
            if not data:
                return None
            path, name = data['path'], data['name']
            path = os.path.join(path, name + '.xml')
        
        if not os.path.exists(path):
            cmds.warning('Could not find cache: %r' % path)
            return
        
        return path
    
    def setCachePath(self, path):
        
        # If we can seperate all the data out, then do so.
        entities = sgfs.entities_from_path(path)
        if entities and entities[0]['type'] == 'Task':
            task = entities[0]
            shot = task.parent()
            if shot['type'] == 'Shot':
                task_path = sgfs.path_for_entity(task)
                relative = os.path.relpath(path, task_path)
                m = re.match(r'maya/data/(geocache|geo_cache|geoCache)/(\w+)/(\w+)/\3.xml', relative)
                if m:
                    _, cache_name, object_name = m.groups()
                    shot_i = self._entity_combo.indexWithText(shot['code'])
                    if shot_i is None:
                        self._entity_combo.insertItem(0, shot['code'], (sgfs.path_for_entity(shot), shot))
                        shot_i = 0
                    # Assume that the combos automatically trigger the next
                    # the automatically populate.
                    self._entity_combo.setCurrentIndex(shot_i)
                    self._populate_step_combo()
                    self._step_combo.setCurrentIndex(self._step_combo.indexWithText(task['step']['code']))
                    self._populate_cache_combo()
                    self._cache_combo.setCurrentIndex(self._cache_combo.indexWithText(cache_name))
                    self._populate_object_combo()
                    self._object_combo.setCurrentIndex(self._object_combo.indexWithText(object_name))
                    return
        
        self._entity_combo.setCurrentIndex(self._entity_combo.count() - 1)
        self._on_entity_changed()
        workspace = cmds.workspace(q=True, directory=True)
        relative = os.path.relpath(path, workspace)
        if relative.startswith('.'):
            self._cache_field.setText(path)
        else:
            self._cache_field.setText(relative)
    
    def channels(self):
        cache_path = self.cachePath()
        if not cache_path:
            return []
        else:
            return cmds.cacheFile(cache_path, q=True, channel=True) or []
             


class Dialog(QtGui.QDialog):

    def __init__(self):
        super(Dialog, self).__init__()
        self._caches = []
        self._init_ui()
        self._populate_existing()
    
    def _init_ui(self):
        self.setWindowTitle('Geocache Import')
        self.setWindowFlags(Qt.Tool)
        self.setMinimumWidth(700)
        self.setMinimumHeight(550)
        
        main_layout = QtGui.QVBoxLayout()
        self.setLayout(main_layout)
        
        self._scroll_widget = area = QtGui.QScrollArea()
        main_layout.addWidget(area)
        area.setFrameShape(QtGui.QFrame.NoFrame)
        area.setWidgetResizable(True)
                
        area_widget = QtGui.QWidget()
        area.setWidget(area_widget)
        self._scroll_layout = QtGui.QVBoxLayout()
        area_widget.setLayout(self._scroll_layout)
        self._scroll_layout.addStretch()
        
        button_layout = QtGui.QHBoxLayout()
        main_layout.addLayout(button_layout)
        
        self._link_button = button = QtGui.QPushButton("Add Geocache...")
        button.setMinimumSize(button.sizeHint().expandedTo(QtCore.QSize(100, 0)))
        button_layout.addWidget(button)
        button.clicked.connect(self._on_add_geocache)
        
        button_layout.addStretch()
        
        self._apply_button = button = QtGui.QPushButton("Apply")
        button.setMinimumSize(button.sizeHint().expandedTo(QtCore.QSize(100, 0)))
        button_layout.addWidget(button)
        button.clicked.connect(self._on_apply_clicked)
        self._save_button = button = QtGui.QPushButton("Save")
        button.setMinimumSize(button.sizeHint().expandedTo(QtCore.QSize(100, 0)))
        button_layout.addWidget(button)
        button.clicked.connect(self._on_save_clicked)
        
    
    def _populate_existing(self):
        
        switches = cmds.ls(type="historySwitch")
        for switch in []:#switches:
            cache = None
            selection = []
            for connection in cmds.listConnections(switch, source=True):
                type_ = cmds.nodeType(connection)
                if type_ == 'cacheFile':
                    cache = cmds.cacheFile(connection, q=True, fileName=True)[0]
                elif type_ in ('mesh', 'transform'):
                    selection.append(connection)
            
            if not cache or not selection:
                continue
            
            link = Geocache()
            link.setCachePath(cache)
            link.setSelection(selection)
            
            self._caches.append(link)
            self._scroll_layout.insertWidget(self._scroll_layout.count() - 1, link)
        
        if not self._caches:
            self._on_add_geocache()
    
    def _on_add_geocache(self):
        link = Geocache()
        self._caches.append(link)
        self._scroll_layout.insertWidget(self._scroll_layout.count() - 1, link)
    
    def _on_save_clicked(self):
        self._on_apply_clicked()
        self.close()
    
    def _on_apply_clicked(self):
        print 'APPLY'
        
        original_selection = cmds.ls(sl=True)
        for link in self._caches:
            
            cache_path = link.cachePath()
            mapping = link.mapping()
            
            if not selection:
                continue
            
            # Delete existing caches.
            history = set()
            for node in selection:
                try:
                    history.update(cmds.listHistory(node, levels=2))
                except TypeError:
                    pass
            caches = []
            for node in history:
                if cmds.nodeType(node) == 'cacheFile':
                    caches.append(node)
            if caches:
                caches = list(set(caches))
                if len(caches) == 1 and cmds.cacheFile(caches[0], q=True, fileName=True)[0] == cache:
                    print '# Cache already up to date: %r' % cache
                    continue
                else:
                    print '# Removing old caches:'
                    for old in caches:
                        print '#\t-', cmds.cacheFile(old, q=True, fileName=True)[0]
                    mel.eval('deleteCacheFile(3, {"keep", "%s", "geometry"})' % (
                        ','.join(caches),
                    ))
            
            if cache is None:
                continue
            print '# Connecting:', cache
            
            # When a cache is created Maya creates a new shape node with
            # "Deformed" appended to it. When the cache is deleted, Maya does
            # not restore the network to it's original state, so the shapeNode
            # is still named deformed. Trying to re-cache once this has
            # happened breaks the import as the expected names have changed
            # from the export. To avoid this, the transform node is always
            # selected instead of the shape. The shape node is whats exported
            # in the original cache.
            cmds.select(clear=True)
            clean_selection = []
            for name in selection:
                type_ = cmds.nodeType(name)
                if type_ == 'mesh':
                    clean_selection.append(cmds.listRelatives(name, parent=True)[0])
                elif type_ == 'transform':
                    clean_selection.append(name)
            cmds.select(clean_selection, replace=True)
            
            channels = set(x.split(':')[-1] for x in cmds.cacheFile(
                query=True,
                fileName=cache,
                channelName=True,
            ) or [])
            
            clean_selection = [x for x in clean_selection if comparison_name(x) in channels]
            
            mel.eval('doImportCacheFile("%s", "Best Guess", {}, {})' % (
                cache,
                # ', '.join('"%s"' % x for x in selection),
            ))
        
        # Restore selection.
        if original_selection:
            cmds.select(original_selection, replace=True)
        else:
            cmds.select(clear=True)
            
__also_reload__ = ['ks.core.scene_name.core']
def __before_reload__():
    if dialog:
        dialog.close()

dialog = None

def run():
    
    global dialog
    
    if dialog:
        dialog.close()
    
    dialog = Dialog()    
    dialog.show()
        