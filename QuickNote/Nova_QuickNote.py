import gi
print("🔍 Nova QuickNote sta avviando...")

gi.require_version("Gtk", "3.0")
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, Gtk, Pango

import subprocess
from docx import Document

class NovaQuickNote(Gtk.Window):
    def __init__(self):
        super().__init__(title="Nova QuickNote")
        self.set_default_size(900, 600)
        self.current_tag = None

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.add(box)

        # Sidebar
        self.sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.sidebar_box.set_size_request(200, -1)

        # Pulsanti principali
        new_btn = Gtk.Button(label="🆕 Nuovo Documento")
        open_btn = Gtk.Button(label="📂 Apri File")
        text_mode_btn = Gtk.Button(label="✍️ Write")
        save_btn = Gtk.Button(label="📅 Salva")
        export_btn = Gtk.Button(label="📄 Esporta")
        cloud_btn = Gtk.Button(label="☁️ Salva su Cloud")

        self.main_buttons = [new_btn, open_btn, text_mode_btn, save_btn, export_btn, cloud_btn]
        for btn in self.main_buttons:
            self.sidebar_box.pack_start(btn, False, False, 0)

        # TextView
        self.textview = Gtk.TextView()
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.buffer = self.textview.get_buffer()
        self.textview.connect("key-press-event", self.handle_new_line)

        scroll = Gtk.ScrolledWindow()
        scroll.add(self.textview)

        box.pack_start(self.sidebar_box, False, False, 0)
        box.pack_start(scroll, True, True, 0)

        self.create_tags()
        self.text_tools_box = None

        # Connessioni
        new_btn.connect("clicked", self.new_document)
        open_btn.connect("clicked", self.open_file)
        save_btn.connect("clicked", self.save_file)
        export_btn.connect("clicked", self.export_dialog)
        cloud_btn.connect("clicked", self.save_to_cloud)
        text_mode_btn.connect("clicked", self.show_text_tools)

    def create_tags(self):
        self.buffer.create_tag("title", weight=Pango.Weight.BOLD, size=24 * Pango.SCALE)
        self.buffer.create_tag("title1", weight=Pango.Weight.BOLD, size=18 * Pango.SCALE)
        self.buffer.create_tag("title2", weight=Pango.Weight.BOLD, size=14 * Pango.SCALE)
        self.buffer.create_tag("bold", weight=Pango.Weight.BOLD)
        self.buffer.create_tag("italic", style=Pango.Style.ITALIC)
        self.buffer.create_tag("bullet", left_margin=20, indent=10)
        self.buffer.create_tag("numbered", left_margin=20, indent=10)

    def handle_new_line(self, widget, event):
        if event.keyval == Gdk.KEY_Return:
            cursor_position = self.buffer.get_insert()
            iter_position = self.buffer.get_iter_at_mark(cursor_position)
            start_line = iter_position.copy()
            start_line.set_line_offset(0)
            previous_line = self.buffer.get_text(start_line, iter_position, False)

        # Elenco puntato
            if previous_line.strip().startswith("•"):
                self.buffer.insert(iter_position, "\n• ")
                return True

        # Elenco numerato
            elif previous_line.strip().split(".")[0].isdigit():
                try:
                    number = int(previous_line.strip().split(".")[0])
                    self.buffer.insert(iter_position, f"\n{number + 1}. ")
                    return True
                except ValueError:
                    pass

    # Comportamento predefinito: consenti "invio"
            return False


    def show_text_tools(self, button):
        if self.text_tools_box is None:
            self.text_tools_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

            title_btn = Gtk.Button(label="TITOLO")
            title1_btn = Gtk.Button(label="Titolo 1")
            title2_btn = Gtk.Button(label="Titolo 2")
            bold_btn = Gtk.Button(label="Grassetto")
            italic_btn = Gtk.Button(label="Corsivo")
            bullet_btn = Gtk.Button(label="• Elenco puntato")
            numbered_btn = Gtk.Button(label="1. Elenco numerato")
            back_btn = Gtk.Button(label="Indietro")

            for btn in [title_btn, title1_btn, title2_btn, bold_btn, italic_btn, bullet_btn, numbered_btn, back_btn]:
                self.text_tools_box.pack_start(btn, False, False, 0)


            self.sidebar_box.pack_start(self.text_tools_box, False, False, 0)

            title_btn.connect("clicked", lambda x: self.apply_style_to_selection("title"))
            title1_btn.connect("clicked", lambda x: self.apply_style_to_selection("title1"))
            title2_btn.connect("clicked", lambda x: self.apply_style_to_selection("title2"))
            bold_btn.connect("clicked", lambda x: self.apply_style_to_selection("bold"))
            italic_btn.connect("clicked", lambda x: self.apply_style_to_selection("italic"))
            bullet_btn.connect("clicked", lambda x: self.apply_style_to_selection("bullet"))
            numbered_btn.connect("clicked", lambda x: self.apply_style_to_selection("numbered"))
            back_btn.connect("clicked", self.hide_tools)
            


        self.text_tools_box.show_all()
        for btn in self.main_buttons:
            btn.hide()

    def hide_tools(self, button):
        if self.text_tools_box:
            self.text_tools_box.hide()
        for btn in self.main_buttons:
            btn.show()

    def apply_style_to_selection(self, tag_name):
        if self.buffer.get_has_selection():
            start, end = self.buffer.get_selection_bounds()
            text = self.buffer.get_text(start, end, True)
            if tag_name == "bullet":
                formatted_text = "• " + text.replace("\n", "\n• ")
            elif tag_name == "numbered":
                lines = text.split("\n")
                formatted_text = "\n".join([f"{i+1}. {line}" for i, line in enumerate(lines)])
            else:
                self.buffer.apply_tag_by_name(tag_name, start, end)
                return
            self.buffer.delete(start, end)
            self.buffer.insert(start, formatted_text)

    def export_dialog(self, button):
        dialog = Gtk.FileChooserDialog(title="Salva Documento", parent=self, action=Gtk.FileChooserAction.SAVE)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)

        format_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        format_label = Gtk.Label(label="Formato:")
        format_combo = Gtk.ComboBoxText()
        for fmt in ["odt", "doc", "docx", "txt"]:
            format_combo.append_text(fmt)
        format_combo.set_active(2)

        format_box.pack_start(format_label, False, False, 0)
        format_box.pack_start(format_combo, False, False, 0)
        dialog.get_content_area().pack_start(format_box, False, False, 0)

        dialog.show_all()

        if dialog.run() == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            selected_format = format_combo.get_active_text()
            start, end = self.buffer.get_bounds()
            content = self.buffer.get_text(start, end, True)

            if selected_format in ["docx", "doc"]:
                doc = Document()
                doc.add_paragraph(content)
                doc.save(f"{filename}.{selected_format}")
            else:
                with open(f"{filename}.{selected_format}", "w") as f:
                    f.write(content)

            print(f"✅ Esportato in {selected_format}: {filename}.{selected_format}")
        dialog.destroy()

    def save_file(self, button):
        dialog = Gtk.FileChooserDialog(title="Salva File", parent=self, action=Gtk.FileChooserAction.SAVE)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        if dialog.run() == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            start, end = self.buffer.get_bounds()
            content = self.buffer.get_text(start, end, True)
            with open(filename, "w") as f:
                f.write(content)
            print(f"✅ File salvato: {filename}")
        dialog.destroy()

    def open_file(self, button):
        dialog = Gtk.FileChooserDialog(title="Apri un file", parent=self, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        if dialog.run() == Gtk.ResponseType.OK:
            with open(dialog.get_filename(), "r") as f:
                self.buffer.set_text(f.read())
        dialog.destroy()

    def save_to_cloud(self, button):
        print("☁️ Simulazione salvataggio su cloud completata.")

    def new_document(self, button):
        self.buffer.set_text("")
        self.current_tag = None
        print("📄 Nuovo documento creato")

print("💻 Avvio di Gtk...")
app = NovaQuickNote()
app.show_all()
Gtk.main()
