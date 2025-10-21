import os
import sys
import json
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
import pygame


def app_base_dir() -> str:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")


class ProyectorCantos:
    def __init__(self, root):
        self.root = root
        self.root.title("Estrella de David - Cantos")
        self.root.configure(bg="white")
        self.root.attributes('-fullscreen', True)

        # Icono de la ventana / logo
        self.base_dir = app_base_dir()
        self.logo_path = os.path.join(self.base_dir, "estrelladedavid.ico")
        if os.path.exists(self.logo_path):
            try:
                self.root.iconbitmap(self.logo_path)
            except Exception:
                pass

        pygame.mixer.init()

        # Rutas base
        self.carpeta_canciones = os.path.join(self.base_dir, "canciones")
        self.carpeta_playlists = os.path.join(self.base_dir, "playlists")
        os.makedirs(self.carpeta_canciones, exist_ok=True)
        os.makedirs(self.carpeta_playlists, exist_ok=True)

        # Estado
        self.canciones = self.cargar_canciones()
        self.setlist = []
        self.cancion_actual_index = 0
        self.musica_pausada = False
        self.orden_seleccion = []  # nombres en el orden seleccionado
        self.canciones_visibles = [c["nombre"] for c in self.canciones]
        self.playlist_en_edicion_path = None  # para sobrescribir cuando se edita

        # Pantallas
        self.frame_inicio = self._construir_inicio()
        self.frame_seleccion = self._construir_seleccion()
        self.frame_letra = self._construir_letra()
        self.frame_playlists = self._construir_gestor_playlists()

        # Mostrar inicio
        self._mostrar_frame(self.frame_inicio)

        # Atajos y navegación global (no dependen de un menú)
        self.root.bind("<Escape>", self.volver_a_inicio)
        self.root.bind("<Right>", lambda e: self.cancion_siguiente())
        self.root.bind("<Left>", lambda e: self.cancion_anterior())
        self.root.bind("<space>", lambda e: self.play_pause())
        self.root.bind("<Control-s>", lambda e: self.guardar_playlist())
        self.root.bind("<Control-o>", lambda e: self.cargar_playlist_por_dialogo())
        self.root.bind("<Control-n>", lambda e: self.mostrar_menu_armar_playlist())

    # ---------- Construcción de pantallas ----------
    def _construir_inicio(self):
        frame = tk.Frame(self.root, bg="white")

        # Logo (intenta renderizar .ico; si no, solo icono de ventana)
        self.logo_img = None
        if os.path.exists(self.logo_path):
            try:
                self.logo_img = tk.PhotoImage(file=self.logo_path)
            except Exception:
                self.logo_img = None
        if self.logo_img:
            tk.Label(frame, image=self.logo_img, bg="white").pack(pady=(30, 10))

        titulo = tk.Label(
            frame, text="Estrella de David",
            font=("Arial", 56, "bold"), bg="white", fg="#222222"
        )
        titulo.pack(pady=10)

        subt = tk.Label(
            frame, text="Selecciona una opción",
            font=("Arial", 24), bg="white", fg="#444444"
        )
        subt.pack(pady=(0, 20))

        cont = tk.Frame(frame, bg="white")
        cont.pack(expand=True)

        tk.Button(
            cont, text="Seleccionar / Armar playlist",
            font=("Arial", 28, "bold"),
            bg="#1d5aa6", fg="white", bd=0, padx=30, pady=18,
            command=self.mostrar_menu_armar_playlist
        ).grid(row=0, column=0, padx=20, pady=20)

        tk.Button(
            cont, text="Cargar playlist",
            font=("Arial", 28, "bold"),
            bg="#0f6f3b", fg="white", bd=0, padx=30, pady=18,
            command=self.mostrar_gestor_playlists
        ).grid(row=0, column=1, padx=20, pady=20)

        tk.Button(
            frame, text="Cerrar aplicación",
            font=("Arial", 18, "bold"),
            bg="#aa0000", fg="white", bd=0, padx=18, pady=10,
            command=self.cerrar_aplicacion
        ).pack(pady=30)

        return frame

    def _construir_seleccion(self):
        frame = tk.Frame(self.root, bg="white")

        self.label_instrucciones = tk.Label(
            frame, text="Arma o edita tu playlist: busca y selecciona cantos",
            font=("Arial", 36, "bold"), bg="white", fg="#282828"
        )
        self.label_instrucciones.pack(pady=20)

        caja_busqueda = tk.Frame(frame, bg="white")
        caja_busqueda.pack(pady=(0, 10))
        tk.Label(caja_busqueda, text="Buscar:", font=("Arial", 20), bg="white", fg="#333").pack(side="left", padx=(0, 10))

        self.entry_busqueda = tk.Entry(caja_busqueda, font=("Arial", 22), width=32)
        self.entry_busqueda.pack(side="left")
        self.entry_busqueda.bind("<KeyRelease>", self.filtrar_canciones)

        lista_wrap = tk.Frame(frame, bg="white")
        lista_wrap.pack(padx=40, pady=10, fill="both", expand=True)

        self.lista_canciones = tk.Listbox(
            lista_wrap, selectmode=tk.MULTIPLE, font=("Arial", 24),
            bd=0, highlightthickness=0, selectbackground="#d0d0d0", activestyle="none"
        )
        self.lista_canciones.pack(side="left", fill="both", expand=True)

        sb = tk.Scrollbar(lista_wrap)
        sb.pack(side="right", fill="y")
        self.lista_canciones.config(yscrollcommand=sb.set)
        sb.config(command=self.lista_canciones.yview)

        for cancion in self.canciones:
            self.lista_canciones.insert(tk.END, cancion["nombre"])

        self.lista_canciones.bind('<<ListboxSelect>>', self.actualizar_orden_seleccion)

        barra_botones = tk.Frame(frame, bg="white")
        barra_botones.pack(pady=10)

        # Guardar como (siempre disponible)
        tk.Button(
            barra_botones, text="Guardar playlist…",
            font=("Arial", 18, "bold"),
            bg="#0f6f3b", fg="white", bd=0, padx=18, pady=8,
            command=self.guardar_playlist
        ).grid(row=0, column=0, padx=6)

        # Guardar cambios (sobrescribir) solo si venimos de "Editar"
        self.btn_guardar_cambios = tk.Button(
            barra_botones, text="Guardar cambios (sobrescribir)",
            font=("Arial", 18, "bold"),
            bg="#00796b", fg="white", bd=0, padx=18, pady=8,
            command=self.guardar_cambios_sobrescribir
        )
        self.btn_guardar_cambios.grid(row=0, column=1, padx=6)
        self.btn_guardar_cambios.grid_remove()  # oculto por defecto

        tk.Button(
            barra_botones, text="Iniciar Proyección",
            font=("Arial", 22, "bold"),
            bg="#282828", fg="white", bd=0, padx=22, pady=10,
            command=self.cargar_setlist
        ).grid(row=0, column=2, padx=12)

        tk.Button(
            barra_botones, text="Volver al inicio (Esc)",
            font=("Arial", 18, "bold"),
            bg="#444444", fg="white", bd=0, padx=18, pady=8,
            command=self.volver_a_inicio
        ).grid(row=0, column=3, padx=6)

        tk.Button(
            barra_botones, text="Cerrar aplicación",
            font=("Arial", 18, "bold"),
            bg="#aa0000", fg="white", bd=0, padx=18, pady=8,
            command=self.cerrar_aplicacion
        ).grid(row=0, column=4, padx=6)

        return frame

    def _construir_letra(self):
        frame = tk.Frame(self.root, bg="white")

        self.label_titulo = tk.Label(frame, text="", font=("Arial", 50, "bold"), bg="white", fg="black")
        self.label_titulo.pack(pady=20)

        frame_central = tk.Frame(frame, bg="white")
        frame_central.pack(expand=True, fill="both", padx=30, pady=10)

        scrollbar = tk.Scrollbar(frame_central)
        scrollbar.pack(side="right", fill="y")

        self.texto_letra = tk.Text(
            frame_central, font=("Arial Black", 40), bg="white", fg="black",
            wrap="word", bd=0, spacing3=30, yscrollcommand=scrollbar.set
        )
        self.texto_letra.pack(expand=True, fill="both")
        self.texto_letra.tag_configure("center", justify="center")
        scrollbar.config(command=self.texto_letra.yview)

        frame_inferior = tk.Frame(frame, bg="white")
        frame_inferior.pack(fill="x", pady=10)

        tk.Button(
            frame_inferior, text="Volver al menú principal (Esc)",
            font=("Arial", 18, "bold"),
            bg="#444444", fg="white", bd=0, padx=18, pady=8,
            command=self.volver_a_inicio
        ).pack(side="left", padx=20)

        tk.Button(
            frame_inferior, text="Cerrar aplicación",
            font=("Arial", 18, "bold"),
            bg="#aa0000", fg="white", bd=0, padx=18, pady=8,
            command=self.cerrar_aplicacion
        ).pack(side="right", padx=20)

        return frame

    def _construir_gestor_playlists(self):
        frame = tk.Frame(self.root, bg="white")

        titulo = tk.Label(frame, text="Playlists guardadas", font=("Arial", 36, "bold"), bg="white", fg="#222")
        titulo.pack(pady=20)

        lista_wrap = tk.Frame(frame, bg="white")
        lista_wrap.pack(padx=40, pady=10, fill="both", expand=True)

        self.lista_playlists = tk.Listbox(
            lista_wrap, selectmode=tk.SINGLE, font=("Arial", 22),
            bd=0, highlightthickness=0, selectbackground="#d0d0d0", activestyle="none"
        )
        self.lista_playlists.pack(side="left", fill="both", expand=True)

        sb = tk.Scrollbar(lista_wrap)
        sb.pack(side="right", fill="y")
        self.lista_playlists.config(yscrollcommand=sb.set)
        sb.config(command=self.lista_playlists.yview)

        # Doble clic = proyectar
        self.lista_playlists.bind("<Double-Button-1>", lambda e: self._proyectar_playlist_desde_lista())

        barra = tk.Frame(frame, bg="white")
        barra.pack(pady=10)

        tk.Button(
            barra, text="Proyectar seleccionada",
            font=("Arial", 18, "bold"),
            bg="#1d5aa6", fg="white", bd=0, padx=18, pady=8,
            command=self._proyectar_playlist_desde_lista
        ).grid(row=0, column=0, padx=6)

        tk.Button(
            barra, text="Editar seleccionada",
            font=("Arial", 18, "bold"),
            bg="#6a1b9a", fg="white", bd=0, padx=18, pady=8,
            command=self._editar_playlist_desde_lista
        ).grid(row=0, column=1, padx=6)

        tk.Button(
            barra, text="Refrescar",
            font=("Arial", 18, "bold"),
            bg="#0f6f3b", fg="white", bd=0, padx=18, pady=8,
            command=self._refrescar_lista_playlists
        ).grid(row=0, column=2, padx=6)

        tk.Button(
            barra, text="Volver al inicio (Esc)",
            font=("Arial", 18, "bold"),
            bg="#444444", fg="white", bd=0, padx=18, pady=8,
            command=self.volver_a_inicio
        ).grid(row=0, column=3, padx=6)

        self._refrescar_lista_playlists()
        return frame

    # ---------- Navegación entre pantallas ----------
    def _mostrar_frame(self, frame_obj):
        for child in (self.frame_inicio, self.frame_seleccion, self.frame_letra, self.frame_playlists):
            child.pack_forget()
        frame_obj.pack(fill="both", expand=True)

    def volver_a_inicio(self, event=None):
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self.setlist = []
        self.lista_canciones.selection_clear(0, tk.END)
        self.orden_seleccion.clear()
        if hasattr(self, "entry_busqueda"):
            self.entry_busqueda.delete(0, tk.END)
        self.playlist_en_edicion_path = None
        if hasattr(self, "btn_guardar_cambios"):
            self.btn_guardar_cambios.grid_remove()
        self._mostrar_frame(self.frame_inicio)

    def mostrar_menu_armar_playlist(self):
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self.playlist_en_edicion_path = None
        self.btn_guardar_cambios.grid_remove()
        self._mostrar_frame(self.frame_seleccion)

    def mostrar_gestor_playlists(self):
        self._refrescar_lista_playlists()
        self._mostrar_frame(self.frame_playlists)

    # ---------- Gestor de playlists ----------
    def _refrescar_lista_playlists(self):
        self.lista_playlists.delete(0, tk.END)
        archivos = [f for f in os.listdir(self.carpeta_playlists) if f.lower().endswith(".json")]
        archivos.sort(key=str.lower)
        if not archivos:
            self.lista_playlists.insert(tk.END, "— No hay playlists guardadas —")
            self.lista_playlists.config(state="disabled")
        else:
            self.lista_playlists.config(state="normal")
            for f in archivos:
                nombre = os.path.splitext(f)[0]
                self.lista_playlists.insert(tk.END, nombre)

    def _ruta_playlist_por_indice(self, idx):
        archivos = [f for f in os.listdir(self.carpeta_playlists) if f.lower().endswith(".json")]
        archivos.sort(key=str.lower)
        if 0 <= idx < len(archivos):
            return os.path.join(self.carpeta_playlists, archivos[idx])
        return None

    def _leer_playlist(self, ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
        lista_nombres = datos.get("canciones", [])
        if not isinstance(lista_nombres, list) or not lista_nombres:
            raise ValueError("El archivo de playlist no contiene canciones.")
        return datos.get("nombre", os.path.basename(ruta)), lista_nombres

    def _aplicar_lista_nombres(self, lista_nombres):
        nombres_disponibles = {c["nombre"] for c in self.canciones}
        faltantes = [n for n in lista_nombres if n not in nombres_disponibles]
        cargadas = [n for n in lista_nombres if n in nombres_disponibles]

        if faltantes:
            messagebox.showwarning(
                "Aviso",
                "Algunas canciones de la playlist no están disponibles y se omitirán:\n- " +
                "\n- ".join(faltantes)
            )
        if not cargadas:
            raise ValueError("Ninguna canción de la playlist está disponible.")

        self.orden_seleccion = cargadas[:]

    def _proyectar_playlist_desde_lista(self):
        if str(self.lista_playlists.cget("state")) == "disabled":
            return
        sel = self.lista_playlists.curselection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecciona una playlist de la lista.")
            return
        ruta = self._ruta_playlist_por_indice(sel[0])
        if not ruta:
            return
        try:
            _, lista_nombres = self._leer_playlist(ruta)
            self._aplicar_lista_nombres(lista_nombres)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar la playlist:\n{e}")
            return
        # Proyectar inmediatamente a pantalla completa
        self.cargar_setlist()

    def _editar_playlist_desde_lista(self):
        if str(self.lista_playlists.cget("state")) == "disabled":
            return
        sel = self.lista_playlists.curselection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecciona una playlist de la lista.")
            return
        ruta = self._ruta_playlist_por_indice(sel[0])
        if not ruta:
            return
        try:
            _, lista_nombres = self._leer_playlist(ruta)
            self._aplicar_lista_nombres(lista_nombres)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar la playlist:\n{e}")
            return

        # Guardamos path para sobrescribir
        self.playlist_en_edicion_path = ruta
        self._aplicar_seleccion_en_listbox()
        self.btn_guardar_cambios.grid()  # mostrar botón sobrescribir
        self._mostrar_frame(self.frame_seleccion)

    # ---------- Playlists ----------
    def guardar_playlist(self):
        if not self.orden_seleccion:
            messagebox.showwarning("Advertencia", "Selecciona al menos un canto para guardar la playlist.")
            return

        nombre = simpledialog.askstring("Guardar playlist", "Nombre de la playlist:")
        if not nombre:
            return

        seguro = "".join(c for c in nombre if c.isalnum() or c in " -_").strip()
        if not seguro:
            messagebox.showerror("Error", "El nombre no es válido.")
            return

        ruta = os.path.join(self.carpeta_playlists, f"{seguro}.json")
        datos = {"nombre": nombre, "canciones": self.orden_seleccion[:]}

        try:
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Playlist guardada", f"Se guardó como:\n{ruta}")
            self._refrescar_lista_playlists()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar la playlist:\n{e}")

    def guardar_cambios_sobrescribir(self):
        if not self.playlist_en_edicion_path:
            messagebox.showinfo("Info", "No hay una playlist en edición. Usa 'Guardar playlist…' para crear una nueva.")
            return
        if not self.orden_seleccion:
            messagebox.showwarning("Advertencia", "Selecciona al menos un canto para guardar.")
            return
        try:
            with open(self.playlist_en_edicion_path, "r", encoding="utf-8") as f:
                datos = json.load(f)
        except Exception:
            datos = {"nombre": os.path.splitext(os.path.basename(self.playlist_en_edicion_path))[0]}

        datos["canciones"] = self.orden_seleccion[:]
        try:
            with open(self.playlist_en_edicion_path, "w", encoding="utf-8") as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Playlist actualizada", f"Se sobrescribió:\n{self.playlist_en_edicion_path}")
            self._refrescar_lista_playlists()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo sobrescribir la playlist:\n{e}")

    def cargar_playlist_por_dialogo(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar playlist",
            initialdir=self.carpeta_playlists,
            filetypes=[("Playlist JSON", "*.json")]
        )
        if not ruta:
            return
        try:
            _, lista_nombres = self._leer_playlist(ruta)
            self._aplicar_lista_nombres(lista_nombres)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer la playlist:\n{e}")
            return
        # Por diálogo: dejamos al usuario en selección para seguir editando o proyectar
        self.playlist_en_edicion_path = ruta
        self._aplicar_seleccion_en_listbox()
        self.btn_guardar_cambios.grid()
        self._mostrar_frame(self.frame_seleccion)

    # ---------- Canciones y UI ----------
    def cargar_canciones(self):
        canciones = []
        if not os.path.exists(self.carpeta_canciones):
            os.makedirs(self.carpeta_canciones)

        for nombre_carpeta in sorted(os.listdir(self.carpeta_canciones), key=str.lower):
            ruta_carpeta = os.path.join(self.carpeta_canciones, nombre_carpeta)
            if os.path.isdir(ruta_carpeta):
                ruta_audio = os.path.join(ruta_carpeta, "audio.mp3")
                ruta_letra = os.path.join(ruta_carpeta, "letra.txt")
                if os.path.exists(ruta_letra):
                    canciones.append({
                        "nombre": nombre_carpeta,
                        "audio": ruta_audio if os.path.exists(ruta_audio) else None,
                        "letra": ruta_letra
                    })
        return canciones

    def filtrar_canciones(self, event=None):
        filtro = self.entry_busqueda.get().lower()
        self.lista_canciones.delete(0, tk.END)
        self.canciones_visibles = []

        for cancion in self.canciones:
            if filtro in cancion["nombre"].lower():
                self.lista_canciones.insert(tk.END, cancion["nombre"])
                self.canciones_visibles.append(cancion["nombre"])

        self._aplicar_seleccion_en_listbox_existing_visibles()

    def actualizar_orden_seleccion(self, event):
        seleccion_actual = [self.canciones_visibles[i] for i in self.lista_canciones.curselection()]

        # Remueve deseleccionados visibles
        for nombre in list(self.orden_seleccion):
            if nombre in self.canciones_visibles and nombre not in seleccion_actual:
                self.orden_seleccion.remove(nombre)

        # Agrega nuevos al final del orden
        for nombre in seleccion_actual:
            if nombre not in self.orden_seleccion:
                self.orden_seleccion.append(nombre)

    def _aplicar_seleccion_en_listbox(self):
        # Rellena sin filtro para poder marcar todo
        self.lista_canciones.delete(0, tk.END)
        self.canciones_visibles = [c["nombre"] for c in self.canciones]
        for nombre in self.canciones_visibles:
            self.lista_canciones.insert(tk.END, nombre)
        self._aplicar_seleccion_en_listbox_existing_visibles()

    def _aplicar_seleccion_en_listbox_existing_visibles(self):
        self.lista_canciones.selection_clear(0, tk.END)
        index_por_nombre = {self.canciones_visibles[i]: i for i in range(len(self.canciones_visibles))}
        for nombre in self.orden_seleccion:
            if nombre in index_por_nombre:
                self.lista_canciones.selection_set(index_por_nombre[nombre])

    # ---------- Proyección ----------
    def cargar_setlist(self):
        if not self.orden_seleccion:
            messagebox.showwarning("Advertencia", "Selecciona un canto.")
            return

        self.setlist = [c for c in self.canciones if c["nombre"] in self.orden_seleccion]
        self.setlist.sort(key=lambda c: self.orden_seleccion.index(c["nombre"]))
        self.cancion_actual_index = 0

        # Asegurar pantalla completa al proyectar
        self.root.attributes('-fullscreen', True)

        self._mostrar_frame(self.frame_letra)
        self.mostrar_cancion()

    def mostrar_cancion(self):
        if not self.setlist:
            return

        cancion = self.setlist[self.cancion_actual_index]

        try:
            with open(cancion["letra"], "r", encoding="utf-8") as f:
                letra = f.read()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer la letra:\n{e}")
            return

        self.label_titulo.config(text=cancion['nombre'])
        self.texto_letra.delete("1.0", tk.END)
        self.texto_letra.insert(tk.END, letra)
        self.texto_letra.tag_add("center", "1.0", "end")
        self.texto_letra.yview_moveto(0)

        try:
            if cancion["audio"]:
                pygame.mixer.music.load(cancion["audio"])
                pygame.mixer.music.play()
                self.musica_pausada = False
            else:
                pygame.mixer.music.stop()
                self.musica_pausada = False
        except Exception as e:
            messagebox.showwarning("Audio", f"No se pudo reproducir el audio:\n{e}")

    def cancion_siguiente(self):
        if self.setlist:
            self.cancion_actual_index = (self.cancion_actual_index + 1) % len(self.setlist)
            self.mostrar_cancion()

    def cancion_anterior(self):
        if self.setlist:
            self.cancion_actual_index = (self.cancion_actual_index - 1) % len(self.setlist)
            self.mostrar_cancion()

    def play_pause(self):
        if self.musica_pausada:
            pygame.mixer.music.unpause()
            self.musica_pausada = False
        else:
            pygame.mixer.music.pause()
            self.musica_pausada = True

    # ---------- Utilidades ----------
    def cerrar_aplicacion(self):
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ProyectorCantos(root)
    root.mainloop()
