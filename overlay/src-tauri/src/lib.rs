use std::fs;
use std::env;
use std::path::PathBuf;

#[tauri::command]
fn load_device_id() -> String {
    let appdata = env::var("APPDATA").unwrap_or_else(|_| ".".to_string());
    let dir = PathBuf::from(appdata).join("echt");
    fs::create_dir_all(&dir).ok();
    let path = dir.join("device_id");

    if path.exists() {
        fs::read_to_string(&path).unwrap_or_default()
    } else {
        let id = uuid::Uuid::new_v4().to_string();
        fs::write(&path, &id).ok();
        id
    }
}

#[tauri::command]
fn get_game_rect() -> String {
    let appdata = env::var("APPDATA").unwrap_or_else(|_| ".".to_string());
    let path = PathBuf::from(appdata).join("echt").join("game_rect.json");
    fs::read_to_string(&path).unwrap_or_else(|_| "null".to_string())
}

#[tauri::command]
fn set_window_position(window: tauri::Window, x: i32, y: i32) {
    window.set_position(tauri::PhysicalPosition::new(x, y)).ok();
}

#[tauri::command]
fn toggle_visibility(window: tauri::Window) {
    match window.is_visible() {
        Ok(true) => { let _ = window.hide(); }
        Ok(false) => { let _ = window.show(); }
        _ => {}
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }
      Ok(())
    })
    .invoke_handler(tauri::generate_handler![load_device_id, get_game_rect, set_window_position, toggle_visibility])
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
