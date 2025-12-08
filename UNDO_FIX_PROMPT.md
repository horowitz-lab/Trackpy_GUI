# Fix Undo Functionality - Metadata and Errant Particles Not Updating

## Problem Description
When the undo button is clicked in the particle detection window, the following components are not being properly updated with the restored state:

1. **Metadata display** (right side of detection window) - continues to show old parameter values instead of the restored values from the config file
2. **Errant particle text files** - The particle information displayed (e.g., "mass: 450.2") doesn't match the current parameters (e.g., "min_mass: 550"). This indicates that errant particles are being regenerated using stale/old parameters instead of the restored parameters.

## Root Cause Analysis
The `load_spreadsheet_and_config()` function in `src/main.py` has a timing/ordering issue:

1. The config file is replaced and reloaded, but widgets may still have references to the old config
2. The errant particle gallery's `config_manager` is not explicitly updated before regeneration
3. The metadata display is updated, but the config object may not be fully refreshed when it reads metadata
4. Widgets are updated, but the updates may not have propagated before errant particles are regenerated

## Files to Modify
- `src/main.py` - Function: `load_spreadsheet_and_config()` (around lines 279-322)

## Required Fixes

### Fix 1: Ensure Config is Fully Reloaded
After copying the config file, make absolutely sure the config is reloaded:
```python
# After: shutil.copy2(config_file_path, self.project_config.config_path)
# Add:
self.project_config.config.clear()  # Clear old config
self.project_config._load_config()   # Reload from file
# Verify it worked by checking a value
```

### Fix 2: Explicitly Update Errant Particle Gallery Config Manager
Before regenerating errant particles, explicitly set the config_manager:
```python
# BEFORE regenerating errant particles:
if hasattr(self.dw_detection_window, 'errant_particle_gallery'):
    # Explicitly update the config_manager FIRST
    self.dw_detection_window.errant_particle_gallery.set_config_manager(self.project_config)
    # Process events to ensure update propagates
    QApplication.processEvents()
    # THEN regenerate
    self.dw_detection_window.errant_particle_gallery.regenerate_errant_particles()
```

### Fix 3: Update Metadata Display After All Config Updates
Move the metadata display update to AFTER errant particles are regenerated, and ensure config is fresh:
```python
# Update metadata display LAST, after everything else is done
# This ensures the config_manager has the latest values
self.dw_detection_window._update_metadata_display()
```

### Fix 4: Process Events Between Updates
Add `QApplication.processEvents()` calls to ensure UI updates propagate:
- After updating config_manager on detection window
- After updating errant particle gallery config_manager
- Before regenerating errant particles

## Complete Fix Order (in `load_spreadsheet_and_config()`):

1. Replace config file: `shutil.copy2(config_file_path, self.project_config.config_path)`
2. Clear and reload config: `self.project_config.config.clear()` then `self.project_config._load_config()`
3. Update detection window config_manager: `self.dw_detection_window.set_config_manager(self.project_config)`
4. Process events: `QApplication.processEvents()`
5. Explicitly update errant particle gallery config_manager: `self.dw_detection_window.errant_particle_gallery.set_config_manager(self.project_config)`
6. Process events: `QApplication.processEvents()`
7. Update frame range inputs
8. Update particle data and refresh displays
9. Regenerate errant particles: `self.dw_detection_window.errant_particle_gallery.regenerate_errant_particles()`
10. Update parameters info display: `self.dw_detection_window._update_parameters_info()`
11. Update metadata display LAST: `self.dw_detection_window._update_metadata_display()`

## Verification Steps
After implementing the fix, test by:
1. Set parameters (e.g., min_mass = 550)
2. Find particles
3. Change parameters (e.g., min_mass = 100)
4. Find particles again
5. Click Undo
6. Verify:
   - Metadata display shows min_mass = 550 (the restored value)
   - Errant particle info shows min_mass = 550 (matches current parameters)
   - All parameter displays match the restored config values

