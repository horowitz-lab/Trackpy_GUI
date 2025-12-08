# Architecture Review - File Operations and Code Organization

## Executive Summary

The codebase has good separation of concerns with `FileController` and `ProjectManager`, but there are several places where file operations bypass these controllers. This review identifies issues and recommends fixes.

## Current Architecture

### ✅ Well-Designed Components

1. **FileController** (`src/utils/FileController.py`)
   - Handles all file/folder operations
   - Provides methods: `save_particles_data()`, `load_particles_data()`, `save_trajectories_data()`, `load_trajectories_data()`
   - Manages folder paths and file operations

2. **ProjectManager** (`src/utils/ProjectManager.py`)
   - Handles project creation and loading
   - Manages project folder structure
   - Creates default config files

3. **ConfigManager** (`src/utils/ConfigManager.py`)
   - Centralized configuration management
   - Handles config file reading/writing

### ❌ Issues Found

## Issue 1: Direct File Operations in main.py

**Location:** `src/main.py`

**Problems:**
- Line 266: `pd.read_csv(spreadsheet_path)` - Should use `FileController.load_particles_data()`
- Line 267: Uses `file_controller.save_particles_data()` ✅ (Good!)
- Line 283: `os.remove()` for config - Could be in ProjectManager
- Line 286: `shutil.copy2()` for config - Could be in ProjectManager
- Line 370: `shutil.copy2()` for save folder - Should use FileController methods
- Line 373: `pd.DataFrame().to_csv()` - Should use FileController
- Line 379: `shutil.copy2()` for config - Could be in ProjectManager

**Recommendation:**
- Add `FileController.load_particles_data_from_path(external_path)` for loading external files
- Add `FileController.save_to_save_folder()` methods for undo functionality
- Consider moving config file operations to ProjectManager or ConfigManager

## Issue 2: Direct File Operations in UI Widgets

### DW_ParametersWidget.py
**Problems:**
- Line 348: `shutil.copyfile()` for backup - Should use FileController
- Line 351: `pd.DataFrame().to_csv()` for clearing - Should use FileController
- Line 366: `pd.read_csv()` - Should use `file_controller.load_particles_data()`

**Recommendation:**
- Use `file_controller.load_particles_data()` instead of direct `pd.read_csv()`
- Add `FileController.backup_particles_data()` method
- Use `FileController.save_particles_data(pd.DataFrame())` to clear

### LW_ParametersWidget.py
**Problems:**
- Line 211: `pd.read_csv(all_particles_file)` - Should use `file_controller.load_particles_data()`
- Line 233: `pd.read_csv(filtered_particles_file)` - Should use `file_controller.load_particles_data("filtered_particles.csv")`
- Line 289: `trajectories_filtered.to_csv()` - Should use `file_controller.save_trajectories_data()`
- Line 255: `trajectories_all.to_csv()` - Should use `file_controller.save_trajectories_data("all_trajectories.csv")`

**Recommendation:**
- Replace all `pd.read_csv()` with `file_controller.load_particles_data()` or `file_controller.load_trajectories_data()`
- Replace all `.to_csv()` with `file_controller.save_particles_data()` or `file_controller.save_trajectories_data()`

### LW_LinkingWindow.py
**Problems:**
- Line 214: `pd.read_csv(source_path)` - This is for export, might be okay
- Line 218: `df.to_csv()` - This is for export, might be okay
- Line 366: `pd.read_csv(trajectories_path)` - Should use `file_controller.load_trajectories_data()`
- Line 413: `pd.read_csv(trajectories_path)` - Should use `file_controller.load_trajectories_data()`
- Line 470: `pd.read_csv(trajectories_file)` - Should use `file_controller.load_trajectories_data()`

**Recommendation:**
- Use `file_controller.load_trajectories_data()` for reading trajectories
- Export operations (lines 214-218) are okay since they're writing to external locations

### DW_DetectionWindow.py
**Problems:**
- Line 301: `pd.read_csv(all_particles_path)` - Should use `file_controller.load_particles_data()`

**Recommendation:**
- Use `file_controller.load_particles_data()`

### DW_LW_FilteringWidget.py
**Problems:**
- Line 565: `filtered_data.to_csv(output_path, index=False)` - Should use FileController

**Recommendation:**
- Add `FileController.save_filtered_particles_data()` or use existing `save_particles_data()` with filename parameter

## Issue 3: ParticleProcessing.py File Operations

**Status:** ✅ **ACCEPTABLE**
- Uses global `file_controller` instance
- File operations are part of processing logic (saving errant particles, JSON metadata)
- This is appropriate for a processing module

## Issue 4: Dead Code Found

### Dead Code in main.py
- **Lines 44-45:** `self.win_width` and `self.win_height` - Initialized but never used
- **Recommendation:** Remove these unused attributes

### Potentially Unused FileController Methods
- `create_errant_distance_links_folder()` - Not found in usage search
- `get_all_frame_paths()` - Not found in usage search  
- `cleanup_temp_folders()` - Not found in usage search

**Recommendation:** 
- Verify if these methods are actually needed
- If unused, remove them or document why they exist for future use

## Recommendations Summary

### High Priority
1. **Refactor main.py** to use FileController for all particle/trajectory file operations
2. **Refactor UI widgets** to use FileController methods instead of direct pandas operations
3. **Add missing FileController methods:**
   - `backup_particles_data()` - for creating backups
   - `load_particles_data_from_path(external_path)` - for loading external files
   - `save_to_save_folder(data, filename)` - for undo functionality
   - `save_filtered_particles_data()` - for filtered data

### Medium Priority
4. **Move config file operations** to ProjectManager or ConfigManager
5. **Standardize error handling** for file operations

### Low Priority
6. **Add file operation logging** for debugging
7. **Consider adding file validation** methods

## Code Quality Notes

### Good Practices Found
- ✅ Centralized refresh functions (`refresh_detection_ui()`, `refresh_linking_ui()`)
- ✅ Signal-based architecture for UI updates
- ✅ Dependency injection for FileController and ConfigManager
- ✅ Clear separation between UI and business logic

### Areas for Improvement
- ⚠️ Some file operations bypass FileController
- ⚠️ Inconsistent use of FileController methods
- ⚠️ Some duplicate file path construction logic

