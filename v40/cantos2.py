import os
import tkinter as tk
from tkinter import messagebox
import pygame


class ProyectorCantos:
    def __init__(self, root):
        self.root = root
        self.root.title("Estrella de David")
        self.root.configure(bg="white")
        self.root.attributes('-fullscreen', True)

        pygame.mixer.init()

        self.canciones = self.cargar_canciones()
        self.setlist = []
        self.cancion_actual_index = 0
        self.musica_pausada = False

        self.orden_seleccion = []
        self.canciones_visibles = [c["nombre"] for c in self.canciones]

        self.frame_seleccion = tk.Frame(self.root, bg="white")
        self.frame_seleccion.pack(fill="both", expand=True)

        self.label_instrucciones = tk.Label(
            self.frame_seleccion,
            text="Estrella de David cantos",
            font=("Arial", 40, "bold"),
            bg="white",
            fg="#282828"
        )
        self.label_instrucciones.pack(pady=30)

        self.entry_busqueda = tk.Entry(
            self.frame_seleccion,
            font=("Arial", 24),
            width=30
        )
        self.entry_busqueda.pack(pady=10)
        self.entry_busqueda.bind("<KeyRelease>", self.filtrar_canciones)

        self.lista_canciones = tk.Listbox(
            self.frame_seleccion,
            selectmode=tk.MULTIPLE,
            font=("Arial", 24),
            bd=0,
            highlightthickness=0,
            selectbackground="#d0d0d0",
            activestyle="none"
        )
        self.lista_canciones.pack(padx=40, pady=20, fill="both", expand=True)

        for cancion in self.canciones:
            self.lista_canciones.insert(tk.END, cancion["nombre"])

        self.lista_canciones.bind('<<ListboxSelect>>', self.actualizar_orden_seleccion)

        self.boton_cargar_setlist = tk.Button(
            self.frame_seleccion,
            text="Iniciar Proyección",
            font=("Arial", 28, "bold"),
            bg="#282828",
            fg="white",
            bd=0,
            padx=20,
            pady=10,
            command=self.cargar_setlist
        )
        self.boton_cargar_setlist.pack(pady=30)

        self.boton_salir = tk.Button(
            self.frame_seleccion,
            text="Salir",
            font=("Arial", 24, "bold"),
            bg="#aa0000",
            fg="white",
            bd=0,
            padx=20,
            pady=10,
            command=self.root.destroy
        )
        self.boton_salir.pack(pady=10)

        self.frame_letra = tk.Frame(self.root, bg="white")

        self.label_titulo = tk.Label(
            self.frame_letra,
            text="",
            font=("Arial", 50, "bold"),
            bg="white",
            fg="black"
        )
        self.label_titulo.pack(pady=20)

        self.frame_central = tk.Frame(self.frame_letra, bg="white")
        self.frame_central.pack(expand=True, fill="both", padx=30, pady=10)

        self.scrollbar = tk.Scrollbar(self.frame_central)
        self.scrollbar.pack(side="right", fill="y")

        self.texto_letra = tk.Text(
            self.frame_central,
            font=("Arial Black", 40),
            bg="white",
            fg="black",
            wrap="word",
            bd=0,
            spacing3=30,
            yscrollcommand=self.scrollbar.set
        )
        self.texto_letra.pack(expand=True, fill="both")

        self.texto_letra.tag_configure("center", justify="center")
        self.scrollbar.config(command=self.texto_letra.yview)

        self.root.bind("<Escape>", self.volver_a_seleccion)
        self.root.bind("<Right>", lambda e: self.cancion_siguiente())
        self.root.bind("<Left>", lambda e: self.cancion_anterior())
        self.root.bind("<space>", lambda e: self.play_pause())

    def cargar_canciones(self):
        canciones = []
        carpeta_canciones = "canciones"
        if not os.path.exists(carpeta_canciones):
            os.makedirs(carpeta_canciones)

        for nombre_carpeta in os.listdir(carpeta_canciones):
            ruta_carpeta = os.path.join(carpeta_canciones, nombre_carpeta)
            if os.path.isdir(ruta_carpeta):
                ruta_audio = os.path.join(ruta_carpeta, "audio.mp3")
                ruta_letra = os.path.join(ruta_carpeta, "letra.txt")
                if os.path.exists(ruta_audio) and os.path.exists(ruta_letra):
                    canciones.append({
                        "nombre": nombre_carpeta,
                        "audio": ruta_audio,
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

        
        for i, nombre in enumerate(self.canciones_visibles):
            if nombre in self.orden_seleccion:
                self.lista_canciones.selection_set(i)

    def actualizar_orden_seleccion(self, event):
        seleccion_actual = [
            self.canciones_visibles[i]
            for i in self.lista_canciones.curselection()
        ]

        
        for nombre in self.canciones_visibles:
            if nombre in self.orden_seleccion and nombre not in seleccion_actual:
                self.orden_seleccion.remove(nombre)

        
        for nombre in seleccion_actual:
            if nombre not in self.orden_seleccion:
                self.orden_seleccion.append(nombre)

    def cargar_setlist(self):
        if not self.orden_seleccion:
            messagebox.showwarning("Advertencia", "Debes seleccionar al menos un canto.")
            return

        self.setlist = [c for c in self.canciones if c["nombre"] in self.orden_seleccion]
        self.setlist.sort(key=lambda c: self.orden_seleccion.index(c["nombre"]))
        self.cancion_actual_index = 0

        self.frame_seleccion.pack_forget()
        self.frame_letra.pack(fill="both", expand=True)

        self.mostrar_cancion()

    def mostrar_cancion(self):
        if not self.setlist:
            return

        cancion = self.setlist[self.cancion_actual_index]

        with open(cancion["letra"], "r", encoding="utf-8") as f:
            letra = f.read()

        self.label_titulo.config(text=cancion['nombre'])
        self.texto_letra.delete("1.0", tk.END)
        self.texto_letra.insert(tk.END, letra)
        self.texto_letra.tag_add("center", "1.0", "end")
        self.texto_letra.yview_moveto(0)

        pygame.mixer.music.load(cancion["audio"])
        pygame.mixer.music.play()
        self.musica_pausada = False

    def volver_a_seleccion(self, event=None):
        pygame.mixer.music.stop()
        self.frame_letra.pack_forget()
        self.frame_seleccion.pack(fill="both", expand=True)
        self.setlist = []
        self.lista_canciones.selection_clear(0, tk.END)
        self.orden_seleccion.clear()

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


if __name__ == "__main__":
    root = tk.Tk()
    app = ProyectorCantos(root)
    root.mainloop()
