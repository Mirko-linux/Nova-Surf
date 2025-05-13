import gi
import threading
import time
import json
import os
import locale
import re
from pathlib import Path
from gettext import gettext as _
import webbrowser
from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import google.generativeai as genai
from dotenv import load_dotenv

gi.require_version("Gtk", "3.0")
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, Gtk, Pango, GLib, GObject

# Configurazione traduzioni
LOCALE_DIR = Path(__file__).parent / "locale"
locale.bindtextdomain('novaquicknote', LOCALE_DIR)
locale.textdomain('novaquicknote')

class Settings:
    def __init__(self):
        self.config_dir = os.path.join(os.path.expanduser("~"), ".config", "novaquicknote")
        self.config_file = os.path.join(self.config_dir, "settings.json")
        self.default_settings = {
            "window_size": [900, 600],
            "sidebar_position": "left",
            "theme": "system",
            "language": "auto",
            "font": "Sans 11",
            "toolbar_visible": True,
            "statusbar_visible": True
        }
        self.current_settings = {}
        
        self._ensure_config_dir()
        self.load_settings()
    
    def _ensure_config_dir(self):
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
    
    def load_settings(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.current_settings = json.load(f)
            else:
                self.current_settings = self.default_settings.copy()
        except:
            self.current_settings = self.default_settings.copy()
    
    def save_settings(self):
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.current_settings, f, indent=4)
            return True
        except:
            return False
    
    def get(self, key):
        return self.current_settings.get(key, self.default_settings.get(key))
    
    def set(self, key, value):
        self.current_settings[key] = value

class ArcadiaAI:
    def __init__(self):
        self.gemini_model = None
        self.setup_gemini()
        self.risposte_predefinite = self._carica_risposte_predefinite()
        
    def setup_gemini(self):
        """Configura il modello Gemini"""
        if GOOGLE_API_KEY:
            try:
                genai.configure(api_key=GOOGLE_API_KEY)
                self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
                print("✅ Gemini 1.5 configurato con successo!")
            except Exception as e:
                print(f"❌ Errore configurazione Gemini: {str(e)}")
                self.gemini_model = None
    
    def _carica_risposte_predefinite(self):
        """Carica le risposte predefinite per domande comuni"""
        return {
            "chi sei": _("Sono ArcadiaAI, un chatbot open source basato su Gemini 1.5 Flash."),
            "cosa sai fare": _("Posso aiutarti a scrivere, correggere, generare idee e molto altro usando l'AI di Google!"),
            "chi è tobia testa": _("Tobia Testa è un micronazionalista leonense noto per la sua attività nella Repubblica di Arcadia."),
            "chi è mirko yuri donato": _("Mirko Yuri Donato è il creatore di Nova QuickNote e altri progetti open source."),
            "cos'è nova quicknote": _("Nova QuickNote è un editor di testo libero e open source con integrazione AI avanzata."),
            "come funziona": _("Scrivi qualsiasi richiesta e userò Gemini 1.5 Flash per generare la risposta migliore!"),
            "grazie": _("Di niente! Sono felice di esserti stato utile. 😊"),
        }
    
    def _check_risposta_predefinita(self, messaggio):
        """Verifica se la domanda ha una risposta predefinita"""
        messaggio_pulito = re.sub(r'[^\w\s]', '', messaggio.lower()).strip()
        for domanda, risposta in self.risposte_predefinite.items():
            if domanda in messaggio_pulito:
                return risposta
        return None
    
    def genera_risposta(self, prompt):
        """Genera una risposta usando Gemini o risposte predefinite"""
        # Prima controlla se c'è una risposta predefinita
        risposta = self._check_risposta_predefinita(prompt)
        if risposta:
            return risposta
            
        if not self.gemini_model:
            return "❌ ArcadiaAI non è disponibile. Configurazione mancante (GOOGLE_API_KEY)."
            
        try:
            response = self.gemini_model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": 2000,
                    "temperature": 0.7
                }
            )
            return response.text if response.text else "❌ Nessuna risposta generata"
        except Exception as e:
            print(f"Errore generazione contenuto: {str(e)}")
            return f"❌ Errore durante la generazione: {str(e)}"

class NovaQuickNote(Gtk.Window):
    def __init__(self):
        super().__init__(title=_("Nova QuickNote"))
        
        # Carica impostazioni
        self.settings = Settings()
        self._setup_settings()
        
        # Configura finestra
        self.set_default_size(*self.settings.get("window_size"))
        self.current_tag = None
        self.modified = False
        self.text_tools_box = None
        
        # Inizializza ArcadiaAI con Gemini
        self.arcadia_ai = ArcadiaAI()
        self.ia_server_running = GOOGLE_API_KEY is not None

        # Crea interfaccia
        self._setup_ui()
        self._setup_actions()
        self._apply_settings()
        self.create_tags()
        self.setup_styles()
        
        # Connessioni
        self.connect("delete-event", self.on_window_delete)
        self.connect("configure-event", self._on_window_configure)

    def _setup_settings(self):
        """Applica le impostazioni iniziali"""
        # Imposta lingua
        lang = self.settings.get("language")
        if lang != "auto":
            os.environ['LANGUAGE'] = lang
        
        # Imposta tema
        self._apply_theme(self.settings.get("theme"))

    def _setup_ui(self):
        """Crea l'interfaccia utente"""
        # Main box
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(self.main_box)
        
        # Barra degli strumenti superiore
        self.headerbar = Gtk.HeaderBar()
        self.headerbar.set_show_close_button(True)
        self.headerbar.set_title(_("Nova QuickNote"))
        self.set_titlebar(self.headerbar)
        
        # Menu app
        self._setup_app_menu()
        
        # Barra strumenti principale
        self.toolbar = Gtk.Toolbar()
        self.main_box.pack_start(self.toolbar, False, False, 0)
        
        # Pannello principale
        self.main_panel = Gtk.Paned()
        self.main_box.pack_start(self.main_panel, True, True, 0)
        
        # Sidebar
        self.sidebar = self._create_sidebar()
        if self.settings.get("sidebar_position") == "left":
            self.main_panel.pack1(self.sidebar, False, False)
        else:
            self.main_panel.pack2(self.sidebar, False, False)
        
        # Area di testo principale
        self._setup_text_area()
        
        # Barra di stato
        self.statusbar = Gtk.Statusbar()
        self.main_box.pack_end(self.statusbar, False, False, 0)
        
        # Finestra ArcadiaAI
        self.arcadiaai_window = None

    def _setup_app_menu(self):
        """Crea il menu dell'applicazione"""
        app_menu = Gtk.Menu()
        
        # Menu File
        file_menu = Gtk.MenuItem.new_with_label(_("File"))
        file_submenu = Gtk.Menu()
        
        new_item = Gtk.MenuItem.new_with_label(_("Nuovo"))
        open_item = Gtk.MenuItem.new_with_label(_("Apri"))
        save_item = Gtk.MenuItem.new_with_label(_("Salva"))
        export_item = Gtk.MenuItem.new_with_label(_("Esporta"))
        
        file_submenu.append(new_item)
        file_submenu.append(open_item)
        file_submenu.append(save_item)
        file_submenu.append(export_item)
        file_menu.set_submenu(file_submenu)
        app_menu.append(file_menu)
        
        # Menu Modifica
        edit_menu = Gtk.MenuItem.new_with_label(_("Modifica"))
        edit_submenu = Gtk.Menu()
        
        undo_item = Gtk.MenuItem.new_with_label(_("Annulla"))
        redo_item = Gtk.MenuItem.new_with_label(_("Ripeti"))
        
        edit_submenu.append(undo_item)
        edit_submenu.append(redo_item)
        edit_menu.set_submenu(edit_submenu)
        app_menu.append(edit_menu)
        
        # Menu Visualizza
        view_menu = Gtk.MenuItem.new_with_label(_("Visualizza"))
        view_submenu = Gtk.Menu()
        
        toolbar_item = Gtk.CheckMenuItem.new_with_label(_("Barra strumenti"))
        statusbar_item = Gtk.CheckMenuItem.new_with_label(_("Barra di stato"))
        
        view_submenu.append(toolbar_item)
        view_submenu.append(statusbar_item)
        view_menu.set_submenu(view_submenu)
        app_menu.append(view_menu)
        
        # Menu Preferenze
        prefs_item = Gtk.MenuItem.new_with_label(_("Preferenze"))
        prefs_item.connect("activate", self._show_preferences)
        app_menu.append(prefs_item)
        
        # Connessioni menu
        new_item.connect("activate", self.new_document)
        open_item.connect("activate", self.open_file)
        save_item.connect("activate", self.save_file)
        export_item.connect("activate", self.export_dialog)
        
        app_menu.show_all()
        
        # Pulsante menu
        menu_btn = Gtk.MenuButton()
        menu_btn.set_popup(app_menu)
        menu_btn.set_image(Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON))
        self.headerbar.pack_end(menu_btn)

    def _create_sidebar(self):
        """Crea la sidebar"""
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        sidebar.set_size_request(200, -1)
        
        # Pulsanti principali
        self.new_btn = Gtk.Button.new_with_label(_("🆕 Nuovo"))
        self.open_btn = Gtk.Button.new_with_label(_("📂 Apri"))
        self.save_btn = Gtk.Button.new_with_label(_("💾 Salva"))
        self.arcadiaai_btn = Gtk.Button.new_with_label(_("✨ ArcadiaAI"))
        self.write_btn = Gtk.Button.new_with_label(_("✍️ Write"))
        
        sidebar.pack_start(self.new_btn, False, False, 0)
        sidebar.pack_start(self.open_btn, False, False, 0)
        sidebar.pack_start(self.save_btn, False, False, 0)
        sidebar.pack_start(self.arcadiaai_btn, False, False, 0)
        sidebar.pack_start(self.write_btn, False, False, 0)
        
        return sidebar

    def _setup_text_area(self):
        """Configura l'area di testo principale"""
        self.textview = Gtk.TextView()
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.buffer = self.textview.get_buffer()
        self.textview.connect("key-press-event", self.handle_new_line)
        self.buffer.connect("changed", self.on_buffer_changed)

        scroll = Gtk.ScrolledWindow()
        scroll.add(self.textview)
        if self.settings.get("sidebar_position") == "left":
            self.main_panel.pack2(scroll, True, True)
        else:
            self.main_panel.pack1(scroll, True, True)

    def _setup_actions(self):
        """Configura le azioni principali"""
        self.new_btn.connect("clicked", self.new_document)
        self.open_btn.connect("clicked", self.open_file)
        self.save_btn.connect("clicked", self.save_file)
        self.arcadiaai_btn.connect("clicked", self.open_arcadiaai_window)
        self.write_btn.connect("clicked", self.show_text_tools)

    def _apply_settings(self):
        """Applica tutte le impostazioni"""
        # Mostra/nascondi barre
        self.toolbar.set_visible(self.settings.get("toolbar_visible"))
        self.statusbar.set_visible(self.settings.get("statusbar_visible"))
        
        # Font
        font_desc = Pango.FontDescription(self.settings.get("font"))
        if font_desc:
            self.textview.override_font(font_desc)

    def _apply_theme(self, theme):
        """Applica il tema selezionato"""
        settings = Gtk.Settings.get_default()
        if theme == "dark":
            settings.set_property("gtk-application-prefer-dark-theme", True)
        elif theme == "light":
            settings.set_property("gtk-application-prefer-dark-theme", False)
        else:  # system
            pass

    def _show_preferences(self, widget):
        """Mostra la finestra delle preferenze"""
        dialog = Gtk.Dialog(title=_("Preferenze"), parent=self, flags=0)
        dialog.add_buttons(_("Annulla"), Gtk.ResponseType.CANCEL, _("Salva"), Gtk.ResponseType.OK)
        
        content_area = dialog.get_content_area()
        
        # Layout tab
        layout_grid = Gtk.Grid(column_spacing=12, row_spacing=12, margin=12)
        
        # Posizione sidebar
        sidebar_label = Gtk.Label(label=_("Posizione sidebar:"), xalign=0)
        sidebar_combo = Gtk.ComboBoxText()
        sidebar_combo.append_text(_("Sinistra"))
        sidebar_combo.append_text(_("Destra"))
        sidebar_combo.set_active(0 if self.settings.get("sidebar_position") == "left" else 1)
        
        # Tema
        theme_label = Gtk.Label(label=_("Tema:"), xalign=0)
        theme_combo = Gtk.ComboBoxText()
        theme_combo.append_text(_("Sistema"))
        theme_combo.append_text(_("Chiaro"))
        theme_combo.append_text(_("Scuro"))
        theme_combo.set_active(["system", "light", "dark"].index(self.settings.get("theme")))
        
        # Lingua
        lang_label = Gtk.Label(label=_("Lingua:"), xalign=0)
        lang_combo = Gtk.ComboBoxText()
        lang_combo.append_text(_("Automatica"))
        lang_combo.append_text("English")
        lang_combo.append_text("Italiano")
        lang_combo.set_active(["auto", "en", "it"].index(self.settings.get("language")))
        
        # Font
        font_label = Gtk.Label(label=_("Font:"), xalign=0)
        font_btn = Gtk.FontButton(font=self.settings.get("font"))
        
        # Aggiungi al layout
        layout_grid.attach(sidebar_label, 0, 0, 1, 1)
        layout_grid.attach(sidebar_combo, 1, 0, 1, 1)
        layout_grid.attach(theme_label, 0, 1, 1, 1)
        layout_grid.attach(theme_combo, 1, 1, 1, 1)
        layout_grid.attach(lang_label, 0, 2, 1, 1)
        layout_grid.attach(lang_combo, 1, 2, 1, 1)
        layout_grid.attach(font_label, 0, 3, 1, 1)
        layout_grid.attach(font_btn, 1, 3, 1, 1)
        
        content_area.pack_start(layout_grid, True, True, 0)
        dialog.show_all()
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            # Salva le impostazioni
            self.settings.set("sidebar_position", "left" if sidebar_combo.get_active() == 0 else "right")
            self.settings.set("theme", ["system", "light", "dark"][theme_combo.get_active()])
            self.settings.set("language", ["auto", "en", "it"][lang_combo.get_active()])
            self.settings.set("font", font_btn.get_font())
            
            self.settings.save_settings()
            self._apply_settings()
            self._apply_theme(self.settings.get("theme"))
            
            dialog.hide()
            # Mostra messaggio che richiede riavvio
            md = Gtk.MessageDialog(parent=self,
                                  flags=0,
                                  message_type=Gtk.MessageType.INFO,
                                  buttons=Gtk.ButtonsType.OK,
                                  text=_("Alcune impostazioni richiedono il riavvio dell'applicazione"))
            md.run()
            md.destroy()
        
        dialog.destroy()

    def _on_window_configure(self, widget, event):
        """Salva le dimensioni della finestra quando cambiano"""
        width, height = self.get_size()
        self.settings.set("window_size", [width, height])
        self.settings.save_settings()

    def setup_styles(self):
        """Configura gli stili CSS per l'applicazione"""
        css_provider = Gtk.CssProvider()
        css = """
        #status-success {
            color: #006600;
        }
        #status-error {
            color: #cc0000;
        }
        .ai-assistant {
            background-color: #f0f7ff;
            border-radius: 5px;
            padding: 5px;
            margin: 5px;
        }
        .assistant-frame {
            border: 1px solid #ccc;
            border-radius: 5px;
            padding: 10px;
            margin: 5px;
        }
        """
        css_provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def on_buffer_changed(self, buffer):
        self.modified = True

    def on_window_delete(self, widget, event):
        if self.modified:
            dialog = Gtk.MessageDialog(
                self,
                0,
                Gtk.MessageType.QUESTION,
                Gtk.ButtonsType.YES_NO,
                _("Ci sono modifiche non salvate. Vuoi salvare prima di uscire?"),
            )
            response = dialog.run()
            dialog.destroy()

            if response == Gtk.ResponseType.YES:
                self.save_file(None)
                Gtk.main_quit()
                return True
            elif response == Gtk.ResponseType.NO:
                Gtk.main_quit()
                return True
            else:
                return True

        Gtk.main_quit()
        return True

    def create_tags(self):
        self.buffer.create_tag("title", weight=Pango.Weight.BOLD, size=24 * Pango.SCALE)
        self.buffer.create_tag("title1", weight=Pango.Weight.BOLD, size=18 * Pango.SCALE)
        self.buffer.create_tag("title2", weight=Pango.Weight.BOLD, size=14 * Pango.SCALE)
        self.buffer.create_tag("bold", weight=Pango.Weight.BOLD)
        self.buffer.create_tag("italic", style=Pango.Style.ITALIC)
        self.buffer.create_tag("bullet", left_margin=20, indent=10)
        self.buffer.create_tag("numbered", left_margin=20, indent=10)
        self.buffer.create_tag("ai_assistant", background="lightgray", paragraph_background="lightgray")

    def handle_new_line(self, widget, event):
        if event.keyval == Gdk.KEY_Return:
            cursor_position = self.buffer.get_insert()
            iter_position = self.buffer.get_iter_at_mark(cursor_position)
            start_line = iter_position.copy()
            start_line.set_line_offset(0)
            previous_line = self.buffer.get_text(start_line, iter_position, False)

            if previous_line.strip().startswith("•"):
                self.buffer.insert(iter_position, "\n• ")
                return True

            elif previous_line.strip().split(".")[0].isdigit():
                try:
                    number = int(previous_line.strip().split(".")[0])
                    self.buffer.insert(iter_position, f"\n{number + 1}. ")
                    return True
                except ValueError:
                    pass
            return False

    def show_text_tools(self, button):
        if self.text_tools_box is None:
            self.text_tools_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

            title_btn = Gtk.Button.new_with_label(_("TITOLO"))
            title1_btn = Gtk.Button.new_with_label(_("Titolo 1"))
            title2_btn = Gtk.Button.new_with_label(_("Titolo 2"))
            bold_btn = Gtk.Button.new_with_label(_("Grassetto"))
            italic_btn = Gtk.Button.new_with_label(_("Corsivo"))
            bullet_btn = Gtk.Button.new_with_label(_("• Elenco puntato"))
            numbered_btn = Gtk.Button.new_with_label(_("1. Elenco numerato"))
            back_btn = Gtk.Button.new_with_label(_("Indietro"))

            for btn in [title_btn, title1_btn, title2_btn, bold_btn, italic_btn, bullet_btn, numbered_btn, back_btn]:
                self.text_tools_box.pack_start(btn, False, False, 0)

            self.sidebar.pack_start(self.text_tools_box, False, False, 0)

            title_btn.connect("clicked", lambda x: self.apply_style_to_selection("title"))
            title1_btn.connect("clicked", lambda x: self.apply_style_to_selection("title1"))
            title2_btn.connect("clicked", lambda x: self.apply_style_to_selection("title2"))
            bold_btn.connect("clicked", lambda x: self.apply_style_to_selection("bold"))
            italic_btn.connect("clicked", lambda x: self.apply_style_to_selection("italic"))
            bullet_btn.connect("clicked", lambda x: self.apply_style_to_selection("bullet"))
            numbered_btn.connect("clicked", lambda x: self.apply_style_to_selection("numbered"))
            back_btn.connect("clicked", self.hide_tools)

        self.text_tools_box.show_all()
        for btn in [self.new_btn, self.open_btn, self.save_btn, self.arcadiaai_btn, self.write_btn]:
            btn.hide()

    def hide_tools(self, button):
        if self.text_tools_box:
            self.text_tools_box.hide()
        for btn in [self.new_btn, self.open_btn, self.save_btn, self.arcadiaai_btn, self.write_btn]:
            btn.show()

    def new_document(self, button):
        self.buffer.set_text("")
        self.current_tag = None
        self.modified = False

    def apply_style_to_selection(self, tag_name):
        if self.buffer.get_has_selection():
            start, end = self.buffer.get_selection_bounds()
            text = self.buffer.get_text(start, end, True)
            if tag_name == "bullet":
                formatted_text = "• " + text.replace("\n", "\n• ")
            elif tag_name == "numbered":
                lines = text.split("\n")
                formatted_text = "\n".join([f"{i + 1}. {line}" for i, line in enumerate(lines)])
            else:
                self.buffer.apply_tag_by_name(tag_name, start, end)
                return
            self.buffer.delete(start, end)
            self.buffer.insert(start, formatted_text)

    def export_dialog(self, button):
        dialog = Gtk.FileChooserDialog(title=_("Salva Documento"), parent=self, action=Gtk.FileChooserAction.SAVE)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)

        format_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        format_label = Gtk.Label(label=_("Formato:"))
        format_combo = Gtk.ComboBoxText()
        for fmt in ["odt", "doc", "docx", "txt", "pdf"]:
            format_combo.append_text(fmt)

        default_format_index = 2
        if default_format_index < len(format_combo.get_model()):
            format_combo.set_active(default_format_index)

        format_box.pack_start(format_label, False, False, 0)
        format_box.pack_start(format_combo, False, False, 0)
        dialog.get_content_area().pack_start(format_box, False, False, 0)

        dialog.show_all()

        if dialog.run() == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            selected_format = format_combo.get_active_text()
            start, end = self.buffer.get_bounds()
            content = self.buffer.get_text(start, end, True)

            if selected_format == "pdf":
                pdf_path = f"{filename}.pdf"
                c = canvas.Canvas(pdf_path, pagesize=A4)
                width, height = A4

                x = 2 * cm
                y = height - 2 * cm
                max_width = width - 4 * cm
                line_height = 14

                from reportlab.pdfbase.pdfmetrics import stringWidth

                for line in content.split("\n"):
                    words = line.split(" ")
                    line_buffer = ""
                    for word in words:
                        test_line = line_buffer + word + " "
                        if stringWidth(test_line, "Helvetica", 12) < max_width:
                            line_buffer = test_line
                        else:
                            c.drawString(x, y, line_buffer.strip())
                            y -= line_height
                            line_buffer = word + " "
                    if line_buffer:
                        c.drawString(x, y, line_buffer.strip())
                        y -= line_height

                    if y < 2 * cm:
                        c.showPage()
                        y = height - 2 * cm

                c.save()
                print(f"✅ Esportato in PDF: {pdf_path}")

            elif selected_format in ["docx", "doc"]:
                doc = Document()
                doc.add_paragraph(content)
                doc.save(f"{filename}.{selected_format}")
                print(f"✅ Esportato in {selected_format}: {filename}.{selected_format}")

            else:
                with open(f"{filename}.{selected_format}", "w") as f:
                    f.write(content)
                print(f"✅ Esportato in {selected_format}: {filename}.{selected_format}")

        dialog.destroy()

    def save_file(self, button):
        dialog = Gtk.FileChooserDialog(title=_("Salva File"), parent=self, action=Gtk.FileChooserAction.SAVE)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        if dialog.run() == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            start, end = self.buffer.get_bounds()
            content = self.buffer.get_text(start, end, True)
            with open(filename, "w") as f:
                f.write(content)
            print(f"✅ File salvato: {filename}")
            self.modified = False
        dialog.destroy()

    def open_file(self, button):
        dialog = Gtk.FileChooserDialog(title=_("Apri un file"), parent=self, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

        if dialog.run() == Gtk.ResponseType.OK:
            with open(dialog.get_filename(), "r") as f:
                self.buffer.set_text(f.read())
                self.modified = False
        dialog.destroy()

    def save_to_cloud(self, button):
        print("☁️ Simulazione salvataggio su cloud completata.")

    def open_arcadiaai_window(self, button):
        self.arcadiaai_window = Gtk.Window(title=_("ArcadiaAI - Assistente"))
        self.arcadiaai_window.set_default_size(500, 400)
        self.arcadiaai_window.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)

        # Frame per l'input
        input_frame = Gtk.Frame(label=_("Richiesta"))
        input_frame.get_style_context().add_class("assistant-frame")
        input_scroll = Gtk.ScrolledWindow()
        input_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        input_scroll.set_min_content_height(100)
        self.input_textview = Gtk.TextView()
        self.input_buffer = self.input_textview.get_buffer()
        input_scroll.add(self.input_textview)
        input_frame.add(input_scroll)
        vbox.pack_start(input_frame, True, True, 0)

        # Pulsanti di azione
        buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        send_btn = Gtk.Button.new_with_label(_("Invia"))
        send_btn.set_tooltip_text(_("Invia la richiesta ad ArcadiaAI"))
        send_btn.connect("clicked", self.send_to_arcadiaai)
        
        insert_btn = Gtk.Button.new_with_label(_("Inserisci Testo"))
        insert_btn.set_tooltip_text(_("Inserisci il testo selezionato dal documento principale"))
        insert_btn.connect("clicked", self.insert_selected_text)
        
        buttons_box.pack_start(send_btn, True, True, 0)
        buttons_box.pack_start(insert_btn, True, True, 0)
        vbox.pack_start(buttons_box, False, False, 0)

        # Frame per l'output
        output_frame = Gtk.Frame(label=_("Risposta"))
        output_frame.get_style_context().add_class("assistant-frame")
        output_scroll = Gtk.ScrolledWindow()
        output_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        output_scroll.set_min_content_height(200)
        self.output_textview = Gtk.TextView()
        self.output_buffer = self.output_textview.get_buffer()
        self.output_textview.set_editable(False)
        self.output_textview.set_wrap_mode(Gtk.WrapMode.WORD)
        output_scroll.add(self.output_textview)
        output_frame.add(output_scroll)
        vbox.pack_start(output_frame, True, True, 0)

        # Pulsanti di applicazione
        apply_buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        apply_btn = Gtk.Button.new_with_label(_("Applica al Documento"))
        apply_btn.set_tooltip_text(_("Aggiungi la risposta al documento principale"))
        apply_btn.connect("clicked", self.apply_arcadiaai_output)
        
        copy_btn = Gtk.Button.new_with_label(_("Copia Risposta"))
        copy_btn.set_tooltip_text(_("Copia la risposta negli appunti"))
        copy_btn.connect("clicked", self.copy_arcadiaai_output)
        
        apply_buttons_box.pack_start(apply_btn, True, True, 0)
        apply_buttons_box.pack_start(copy_btn, True, True, 0)
        vbox.pack_start(apply_buttons_box, False, False, 0)

        # Barra di stato
        self.arcadiaai_status_label = Gtk.Label()
        self.arcadiaai_status_label.set_halign(Gtk.Align.START)
        self.update_arcadiaai_status()
        vbox.pack_start(self.arcadiaai_status_label, False, False, 0)

        self.arcadiaai_window.add(vbox)
        self.arcadiaai_window.show_all()

    def insert_selected_text(self, button):
        """Inserisce il testo selezionato nel documento principale nella casella di input"""
        if self.buffer.get_has_selection():
            start, end = self.buffer.get_selection_bounds()
            selected_text = self.buffer.get_text(start, end, True)
            self.input_buffer.set_text(selected_text)

    def copy_arcadiaai_output(self, button):
        """Copia il testo di output negli appunti"""
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        text = self.output_buffer.get_text(
            self.output_buffer.get_start_iter(),
            self.output_buffer.get_end_iter(),
            True
        )
        clipboard.set_text(text, -1)
        clipboard.store()

    def send_to_arcadiaai(self, button):
        input_text = self.input_buffer.get_text(
            self.input_buffer.get_start_iter(), 
            self.input_buffer.get_end_iter(), 
            True
        )
        
        if not input_text.strip():
            self.output_buffer.set_text(_("Per favore, inserisci una richiesta valida."))
            return
            
        self.output_buffer.set_text(_("Elaborazione in corso..."))
        
        # Aggiungi un indicatore di attività
        spinner = Gtk.Spinner()
        self.arcadiaai_window.get_child().pack_start(spinner, False, False, 0)
        spinner.start()
        
        threading.Thread(
            target=self.interact_with_ia, 
            args=(input_text, spinner),
            daemon=True
        ).start()
        
    def update_output_text(self, text):
        self.output_buffer.set_text(text)

    def interact_with_ia(self, text_to_send, spinner=None):
        """Interagisce con Gemini AI"""
        try:
            # Genera la risposta usando Gemini
            risposta = self.arcadia_ai.genera_risposta(text_to_send)
            
            GLib.idle_add(self.update_output_text, risposta)
        except Exception as e:
            error_msg = f"❌ Errore durante la generazione della risposta: {str(e)}"
            GLib.idle_add(lambda: self.output_buffer.set_text(error_msg))
        finally:
            if spinner:
                GLib.idle_add(spinner.stop)
                GLib.idle_add(spinner.destroy)
                
    def update_arcadiaai_status(self):
        """Aggiorna l'etichetta dello stato di ArcadiaAI"""
        if self.ia_server_running:
            self.arcadiaai_status_label.set_text("🟢 ArcadiaAI - pronto")
            self.arcadiaai_status_label.set_name("status-success")
        else:
            self.arcadiaai_status_label.set_text("🔴 ArcadiaAI non configurato (manca GOOGLE_API_KEY nel file .env)")
            self.arcadiaai_status_label.set_name("status-error")

    def apply_arcadiaai_output(self, button):
        output_text = self.output_buffer.get_text(
            self.output_buffer.get_start_iter(), 
            self.output_buffer.get_end_iter(), 
            True
        )
        
        if output_text.strip():
                       # Applica uno stile speciale al testo inserito
            start_iter = self.buffer.get_end_iter()
            self.buffer.insert(start_iter, "\n\n" + output_text)
            
            # Applica il tag per evidenziare il testo generato dall'AI
            end_iter = self.buffer.get_end_iter()
            start_mark = self.buffer.create_mark(None, start_iter, True)
            self.buffer.apply_tag_by_name(
                "ai_assistant", 
                self.buffer.get_iter_at_mark(start_mark), 
                end_iter
            )
            
            self.modified = True
            
        self.arcadiaai_window.destroy()

if __name__ == '__main__':
    load_dotenv()
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    print("💻 Avvio di Nova QuickNote...")
    app = NovaQuickNote()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()
