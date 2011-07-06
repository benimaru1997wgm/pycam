# -*- coding: utf-8 -*-
"""
$Id: __init__.py 1061 2011-04-12 13:14:12Z sumpfralle $

Copyright 2011 Lars Kruse <devel@sumpfralle.de>

This file is part of PyCAM.

PyCAM is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

PyCAM is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PyCAM.  If not, see <http://www.gnu.org/licenses/>.
"""

# imported later (on demand)
#import gtk

import pycam.Plugins

_GTK_COLOR_MAX = 65535.0


class Models(pycam.Plugins.ListPluginBase):

    UI_FILE = "models.ui"
    COLUMN_ID, COLUMN_NAME, COLUMN_VISIBLE, COLUMN_COLOR, COLUMN_ALPHA = range(5)
    ATTRIBUTE_MAP = {"name": COLUMN_NAME, "visible": COLUMN_VISIBLE,
            "color": COLUMN_COLOR, "alpha": COLUMN_ALPHA}
    ICONS = {"visible": "visible.svg", "hidden": "visible_off.svg"}
    DEFAULT_COLOR = (0.5, 0.5, 1.0, 1.0)

    def setup(self):
        if self.gui:
            import gtk
            self._gtk = gtk
            model_frame = self.gui.get_object("ModelBox")
            model_frame.unparent()
            self.core.register_ui("main", "Models", model_frame, -50)
            model_handling_obj = self.gui.get_object("ModelHandlingNotebook")
            def clear_model_handling_obj():
                for index in range(model_handling_obj.get_n_pages()):
                    model_handling_obj.remove_page(0)
            def add_model_handling_item(item, name):
                model_handling_obj.append_page(item, self._gtk.Label(name))
            self.core.register_ui_section("model_handling",
                    add_model_handling_item, clear_model_handling_obj)
            self._modelview = self.gui.get_object("ModelView")
            for action, obj_name in ((self.ACTION_UP, "ModelMoveUp"),
                    (self.ACTION_DOWN, "ModelMoveDown"),
                    (self.ACTION_DELETE, "ModelDelete"),
                    (self.ACTION_CLEAR, "ModelDeleteAll")):
                self.register_list_action_button(action, self._modelview,
                        self.gui.get_object(obj_name))
            self.gui.get_object("ModelColorButton").connect("color-set",
                    self._set_colors_of_selected_models)
            self.core.register_event("model-selection-changed",
                    self._get_colors_of_selected_models)
            self._modelview.connect("row-activated",
                    self._list_action_toggle_custom, self.COLUMN_VISIBLE)
            self.gui.get_object("ModelVisibleColumn").set_cell_data_func(
                    self.gui.get_object("ModelVisibleSymbol"),
                    self._visualize_visible_state)
            self.gui.get_object("ModelNameColumn").connect("edited",
                    self._edit_model_name)
            selection = self._modelview.get_selection()
            selection.connect("changed",
                    lambda widget, event: self.core.emit_event(event), 
                    "model-selection-changed")
            selection.set_mode(gtk.SELECTION_MULTIPLE)
            self._treemodel = self.gui.get_object("ModelList")
            self._treemodel.clear()
            def update_model():
                if not hasattr(self, "_model_cache"):
                    self._model_cache = {}
                cache = self._model_cache
                for row in self._treemodel:
                    cache[row[self.COLUMN_ID]] = list(row)
                self._treemodel.clear()
                for index, item in enumerate(self):
                    if id(item) in cache:
                        self._treemodel.append(cache[id(item)])
                    else:
                        color = "#%04x%04x%04x" % tuple([int(col * _GTK_COLOR_MAX)
                                for col in self.DEFAULT_COLOR[:3]])
                        self._treemodel.append((id(item), "Model #%d" % index,
                                True, color,
                                int(self.DEFAULT_COLOR[3] * _GTK_COLOR_MAX)))
            self._get_colors_of_selected_models()
            self.register_model_update(update_model)
        self.core.add_item("models", lambda: self)
        return True

    def get_attr(self, model, attr):
        return self.__get_set_attr(model, attr, write=False)

    def set_attr(self, model, attr, value):
        return self.__get_set_attr(model, attr, value=value, write=True)

    def __get_set_attr(self, model, attr, value=None, write=True):
        if attr in self.ATTRIBUTE_MAP:
            col = self.ATTRIBUTE_MAP[attr]
            for index in range(len(self)):
                if self._treemodel[index][self.COLUMN_ID] == id(model):
                    if write:
                        self._treemodel[index][col] = value
                        return
                    else:
                        return self._treemodel[index][col]
            raise IndexError("Model not found: %s" % str(model))
        else:
            raise KeyError("Attribute '%s' is not part of this list: %s" % \
                    (attr, ", ".join(self.ATTRIBUTE_MAP.keys())))

    def _get_colors_of_selected_models(self, widget=None):
        color_button = self.gui.get_object("ModelColorButton")
        models = self.get_selected()
        color_button.set_sensitive(bool(models))
        if models:
            # use the color of the first model
            model = models[0]
            color_str = self.get_attr(model, "color")
            alpha_val = self.get_attr(model, "alpha")
            color_button.set_color(self._gtk.gdk.color_parse(color_str))
            color_button.set_alpha(alpha_val)

    def _set_colors_of_selected_models(self, widget=None):
        color_button = self.gui.get_object("ModelColorButton")
        models = self.get_selected()
        color_str = color_button.get_color().to_string()
        alpha_val = color_button.get_alpha()
        for model in models:
            self.set_attr(model, "color", color_str)
            self.set_attr(model, "alpha", alpha_val)
        self.core.emit_event("visual-item-updated")

    def _edit_model_name(self, cell, path, new_text):
        path = int(path)
        if new_text != self._treemodel[path][self.COLUMN_NAME]:
            self._treemodel[path][self.COLUMN_NAME] = new_text

    def _visualize_visible_state(self, column, cell, model, m_iter):
        visible = model.get_value(m_iter, self.COLUMN_VISIBLE)
        if visible:
            cell.set_property("pixbuf", self.ICONS["visible"])
        else:
            cell.set_property("pixbuf", self.ICONS["hidden"])

    def _list_action_toggle_custom(self, treeview, path, clicked_column,
            force_column=None):
        if force_column is None:
            column = self._modelview.get_columns().index(clicked_column)
        else:
            column = force_column
        self._list_action_toggle(clicked_column, str(path[0]), column)

    def _list_action_toggle(self, widget, path, column):
        path = int(path)
        model = self._treemodel
        model[path][column] = not model[path][column]
        self.core.emit_event("visual-item-updated")

    def get_selected(self):
        return self._get_selected(self._modelview, force_list=True)

    def get_visible(self):
        return [self[index] for index, item in enumerate(self._treemodel)
                if item[self.COLUMN_VISIBLE]]

    def teardown(self):
        if self.gui:
            self.core.unregister_ui("main", self.gui.get_object("ModelBox"))
            self.core.unregister_ui_section("main", "model_handling")
        self.core.set("models", None)
        return True

