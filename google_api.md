# Documentación de la API de Google Drive

## Descripción General

La API de Google Drive te permite crear aplicaciones que aprovechan el almacenamiento en la nube de Google Drive. Puedes desarrollar aplicaciones que se integren con Drive, permitiendo a los usuarios crear, compartir y almacenar archivos.

## Conceptos Clave

*   **Archivo:** Un elemento almacenado en Drive (puede ser un documento, imagen, video, carpeta, etc.).
*   **Carpeta:** Un tipo de archivo contenedor que puede almacenar otros archivos.
*   **Permiso:** Define quién puede acceder a un archivo y qué nivel de acceso tiene.
*   **Unidad Compartida:** Un espacio de almacenamiento donde los archivos pertenecen a un equipo en lugar de a un individuo.

## Autenticación y Autorización

Para utilizar la API, tu aplicación necesita credenciales. Google utiliza el protocolo OAuth 2.0 para la autenticación y autorización.

### Alcances (Scopes)

Los alcances definen el nivel de acceso que solicita tu aplicación. Algunos ejemplos comunes:

*   `https://www.googleapis.com/auth/drive.metadata.readonly`: Ver metadatos de archivos.
*   `https://www.googleapis.com/auth/drive`: Acceso completo a todos los archivos y carpetas.
*   `https://www.googleapis.com/auth/drive.file`: Acceso solo a los archivos creados o abiertos por la aplicación.

## Operaciones con Archivos

### Subir Archivos

Puedes subir archivos de tres maneras:
1.  **Carga simple:** Para archivos pequeños (menos de 5 MB).
2.  **Carga multiparte:** Para subir metadatos y contenido en una sola solicitud.
3.  **Carga reanudable:** Para archivos grandes y mayor confiabilidad ante fallos de red.

#### Ejemplo de Código (Python - Carga Simple)

```python
file_metadata = {'name': 'photo.jpg'}
media = MediaFileUpload('files/photo.jpg', mimetype='image/jpeg')
file = drive_service.files().create(body=file_metadata,
                                    media_body=media,
                                    fields='id').execute()
print('File ID: %s' % file.get('id'))
```

### Descargar Archivos

Para descargar un archivo, utiliza el método `files.get` con el ID del archivo y el parámetro `alt=media`.

#### Ejemplo de Código (Python)

```python
request = drive_service.files().get_media(fileId=file_id)
fh = io.BytesIO()
downloader = MediaIoBaseDownload(fh, request)
done = False
while done is False:
    status, done = downloader.next_chunk()
    print("Download %d%%." % int(status.progress() * 100))
```

### Buscar Archivos

Utiliza el método `files.list` y el parámetro `q` para filtrar resultados.

#### Ejemplos de Consultas (parametro `q`)

*   `name = 'hello'`: Archivos con el nombre exacto "hello".
*   `name contains 'hello'`: Archivos que contienen "hello" en el nombre.
*   `mimeType = 'application/vnd.google-apps.folder'`: Solo carpetas.
*   `'1234567' in parents`: Archivos dentro de la carpeta con ID '1234567'.
*   `trashed = false`: Archivos que no están en la papelera.

## Gestión de Carpetas

Las carpetas en Drive son simplemente archivos con un tipo MIME específico: `application/vnd.google-apps.folder`.

### Crear una Carpeta

```python
file_metadata = {
    'name': 'Invoices',
    'mimeType': 'application/vnd.google-apps.folder'
}
file = drive_service.files().create(body=file_metadata,
                                    fields='id').execute()
print('Folder ID: %s' % file.get('id'))
```

### Mover Archivos entre Carpetas

Para mover un archivo, actualiza sus campos `addParents` y `removeParents`.

```python
file = drive_service.files().update(fileId=file_id,
                                    addParents=folder_id,
                                    removeParents=previous_parents_id,
                                    fields='id, parents').execute()
```

## Permisos y Compartir

Los recursos `permissions` controlan el acceso.

*   **Tipos:** `user`, `group`, `domain`, `anyone`.
*   **Roles:** `owner`, `organizer`, `fileOrganizer`, `writer`, `commenter`, `reader`.

### Compartir un archivo

```python
def callback(request_id, response, exception):
    if exception:
        # Handle error
        print(exception)
    else:
        print("Permission Id: %s" % response.get('id'))

batch = drive_service.new_batch_http_request(callback=callback)
user_permission = {
    'type': 'user',
    'role': 'writer',
    'emailAddress': 'user@example.com'
}
batch.add(drive_service.permissions().create(
        fileId=file_id,
        body=user_permission,
        fields='id',
))
batch.execute()
```

## Límites y Cuotas

*   **Límites de carga:** Varían según el tipo de usuario.
*   **Profundidad de carpetas:** Máximo 100 niveles de anidamiento.
*   **Elementos por carpeta:** Hasta 500,000 elementos por carpeta.

## Migración de v2 a v3

Si estás migrando de la versión 2 a la 3, ten en cuenta:
*   Las búsquedas no devuelven todos los campos por defecto (usa el parámetro `fields`).
*   Los recursos `Children` y `Parents` se han eliminado (usa `files.list` y `files.update`).
*   Las fechas ahora usan el sufijo `Time` (ej. `createdTime` en lugar de `createdDate`).
