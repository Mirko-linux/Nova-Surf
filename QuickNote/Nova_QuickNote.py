import gi
print("🔍 Nova QuickNote sta avviando...")
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Pango
import subprocess

class NovaQuickNote(Gtk.Window):
    def __init__(self):
        super().__init__(title="Nova QuickNote")
        self.set_default_size(900, 600)

        self.current_tag = None

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.add(box)

        # Crea sidebar e assegna a self
        self.sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.sidebar_box.set_size_request(200, -1)

        # Pulsanti principali
        new_btn = Gtk.Button(label="🆕 Nuovo Documento")
        open_btn = Gtk.Button(label="📂 Apri File")
        text_mode_btn = Gtk.Button(label="✍️ Write")
        code_mode_btn = Gtk.Button(label="💻 Edit")
        save_btn = Gtk.Button(label="📅 Salva")
        export_btn = Gtk.Button(label="📄 Esporta")
        cloud_btn = Gtk.Button(label="☁️ Salva su Cloud")

        self.main_buttons = [
            new_btn, open_btn, text_mode_btn,
            code_mode_btn, save_btn, export_btn, cloud_btn
        ]

        for btn in self.main_buttons:
            self.sidebar_box.pack_start(btn, False, False, 0)

        # TextView
        self.textview = Gtk.TextView()
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.buffer = self.textview.get_buffer()
        self.buffer.connect("insert-text", self.on_insert_text)
        scroll = Gtk.ScrolledWindow()
        scroll.add(self.textview)

        box.pack_start(self.sidebar_box, False, False, 0)
        box.pack_start(scroll, True, True, 0)

        self.create_tags()

        # Box strumenti testo
        self.text_tools_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        title_btn = Gtk.Button(label="TITOLO")
        title1_btn = Gtk.Button(label="Titolo 1")
        title2_btn = Gtk.Button(label="Titolo 2")
        bold_btn = Gtk.Button(label="Grassetto")
        italic_btn = Gtk.Button(label="Corsivo")
        font_btn = Gtk.Button(label="🔋 Font e Dimensioni")
        back_btn = Gtk.Button(label="🔙 Indietro")

        for btn in [title_btn, title1_btn, title2_btn, bold_btn, italic_btn, font_btn, back_btn]:
            self.text_tools_box.pack_start(btn, False, False, 0)

        # Box strumenti codice
        self.code_tools_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        lang_btn = Gtk.Button(label="Linguaggio")
        indent_btn = Gtk.Button(label="Correggi Indentazione")
        line_numbers_btn = Gtk.Button(label="Numeri di Riga")
        back_btn_code = Gtk.Button(label="🔙 Indietro")

        for btn in [lang_btn, indent_btn, line_numbers_btn, back_btn_code]:
            self.code_tools_box.pack_start(btn, False, False, 0)

        self.sidebar_box.pack_start(self.text_tools_box, False, False, 0)
        self.sidebar_box.pack_start(self.code_tools_box, False, False, 0)

        self.text_tools_box.set_no_show_all(True)
        self.code_tools_box.set_no_show_all(True)

        self.text_tools_box.hide()
        self.code_tools_box.hide()

        # Connessioni
        new_btn.connect("clicked", self.new_document)
        open_btn.connect("clicked", self.open_file)
        save_btn.connect("clicked", self.save_file)
        export_btn.connect("clicked", self.export_dialog)
        cloud_btn.connect("clicked", self.save_to_cloud)
        text_mode_btn.connect("clicked", self.show_text_tools)
        code_mode_btn.connect("clicked", self.show_code_tools)

        back_btn.connect("clicked", self.hide_tools)
        back_btn_code.connect("clicked", self.hide_tools)

        title_btn.connect("clicked", lambda x: self.apply_style_to_selection("title"))
        title1_btn.connect("clicked", lambda x: self.apply_style_to_selection("title1"))
        title2_btn.connect("clicked", lambda x: self.apply_style_to_selection("title2"))
        bold_btn.connect("clicked", lambda x: self.apply_style_to_selection("bold"))
        italic_btn.connect("clicked", lambda x: self.apply_style_to_selection("italic"))
        font_btn.connect("clicked", self.change_font_size)

    def create_tags(self):
        self.buffer.create_tag("title", weight=Pango.Weight.BOLD, size=24 * Pango.SCALE)
        self.buffer.create_tag("title1", weight=Pango.Weight.BOLD, size=18 * Pango.SCALE)
        self.buffer.create_tag("title2", weight=Pango.Weight.BOLD, size=14 * Pango.SCALE)
        self.buffer.create_tag("bold", weight=Pango.Weight.BOLD)
        self.buffer.create_tag("italic", style=Pango.Style.ITALIC)

    def set_current_tag(self, tag_name):
        self.current_tag = self.buffer.get_tag_table().lookup(tag_name)

    def on_insert_text(self, buffer, location, text, length):
        if self.current_tag:
            start = location.copy()
            end = location.copy()
            end.forward_chars(length)
            buffer.apply_tag(self.current_tag, start, end)

    def apply_style_to_selection(self, tag_name):
        if self.buffer.get_has_selection():
            start, end = self.buffer.get_selection_bounds()
            self.buffer.apply_tag_by_name(tag_name, start, end)

    def show_text_tools(self, button):
        self.text_tools_box.show_all()
        self.code_tools_box.hide()
        for btn in self.main_buttons:
            btn.hide()

    def show_code_tools(self, button):
        self.code_tools_box.show_all()
        self.text_tools_box.hide()
        for btn in self.main_buttons:
            btn.hide()

    def hide_tools(self, button):
        self.text_tools_box.hide()
        self.code_tools_box.hide()
        for btn in self.main_buttons:
            btn.show()

    def change_font_size(self, button):
        dialog = Gtk.Dialog("Font e Dimensione", self, 0, (Gtk.STOCK_OK, Gtk.ResponseType.OK))
        box = dialog.get_content_area()
        label = Gtk.Label(label="Inserisci la dimensione del testo (es. 12):")
        entry = Gtk.Entry()
        box.pack_start(label, False, False, 5)
        box.pack_start(entry, False, False, 5)
        dialog.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            try:
                size = int(entry.get_text()) * Pango.SCALE
                tag = self.buffer.create_tag(None, size=size)
                if self.buffer.get_has_selection():
                    start, end = self.buffer.get_selection_bounds()
                    self.buffer.apply_tag(tag, start, end)
            except ValueError:
                print("Dimensione non valida")
        dialog.destroy()

    def new_document(self, button):
        self.buffer.set_text("")
        self.current_tag = None
        print("📄 Nuovo documento creato")

    def open_file(self, button):
        dialog = Gtk.FileChooserDialog(title="Apri un file", parent=self, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        if dialog.run() == Gtk.ResponseType.OK:
            with open(dialog.get_filename(), "r") as f:
                self.buffer.set_text(f.read())
        dialog.destroy()

    def save_file(self, button):
        dialog = Gtk.FileChooserDialog(title="Salva File", parent=self, action=Gtk.FileChooserAction.SAVE)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        if dialog.run() == Gtk.ResponseType.OK:
            with open(dialog.get_filename(), "w") as f:
                start, end = self.buffer.get_bounds()
                f.write(self.buffer.get_text(start, end, True))
        dialog.destroy()

    def save_to_cloud(self, button):
        print("☁️ Simulazione salvataggio su cloud completata.")

    def export_dialog(self, button):
        dialog = Gtk.Dialog(title="Esporta File", parent=self)
        dialog.set_default_size(250, 100)
        box = dialog.get_content_area()
        label = Gtk.Label(label="Come vuoi esportare il file?")
        box.pack_start(label, True, True, 10)
        odt_btn = Gtk.Button(label="📝 Esporta in ODT")
        pdf_btn = Gtk.Button(label="📄 Esporta in PDF")
        box.pack_start(odt_btn, True, True, 5)
        box.pack_start(pdf_btn, True, True, 5)
        odt_btn.connect("clicked", lambda _: self.export_file("odt", dialog))
        pdf_btn.connect("clicked", lambda _: self.export_file("pdf", dialog))
        dialog.show_all()

    def export_file(self, fmt, dialog):
        dialog.destroy()
        file_dialog = Gtk.FileChooserDialog(title=f"Salva come {fmt.upper()}", parent=self, action=Gtk.FileChooserAction.SAVE)
        file_dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        if file_dialog.run() == Gtk.ResponseType.OK:
            filename = file_dialog.get_filename()
            start, end = self.buffer.get_bounds()
            content = self.buffer.get_text(start, end, True)
            with open("document.txt", "w") as f:
                f.write(content)
            subprocess.run(["pandoc", "document.txt", "-o", f"{filename}.{fmt}"])
            print(f"✅ Esportato in {fmt.upper()}: {filename}.{fmt}")
        file_dialog.destroy()

print("💻 Avvio di Gtk...")
app = NovaQuickNote()
app.show_all()
Gtk.main()
print("👋 Fine del programma.")
