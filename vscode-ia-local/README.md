# IA Local Chat (VS Code Extension)

Extension para usar tu API de IA local directamente dentro de VS Code.

## Panel lateral

- La extension agrega un icono en la Activity Bar llamado **IA Local**.
- Dentro veras la vista **Chat** para conversar con el modelo.

## Funciones

- Chat de texto contra `/chat`.
- Adjuntos de imagen contra `/chat/attachments`.
- Selector de modelo por mensaje.

## Comando

- `IA Local: Enfocar Chat`

## Configuracion

- `iaLocal.apiBaseUrl`: URL base de la API.
- `iaLocal.defaultModel`: modelo por defecto.

## Desarrollo

```bash
npm install
npm run compile
```

Luego abre esta carpeta en VS Code y presiona `F5` para lanzar Extension Development Host.

## Empaquetar

```bash
npx @vscode/vsce package
```
