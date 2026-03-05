from drive_service import drive_service


def find_roots():
    potential_names = ["platzi-downloader", "Platzi", "Cursos", "PlatziViewer", "PlatziCoursesFlat"]

    print("🔍 Buscando carpetas raíz en Google Drive...")
    for name in potential_names:
        folder_id = drive_service.find_folder(name)
        if folder_id:
            print(f"✅ Encontrado '{name}': {folder_id}")
            with open("root_id.txt", "w") as f:
                f.write(folder_id)
            return
        else:
            print(f"❌ No encontrado '{name}'")


if __name__ == "__main__":
    find_roots()
