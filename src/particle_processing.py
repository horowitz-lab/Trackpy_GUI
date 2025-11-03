"""
Particle Processing Module

Description: Combined particle detection, tracking, and processing functions.
             Includes TrackPy wrapper functions and particle processing workflows.
"""

import cv2
import os
import numpy as np
import pandas as pd
import trackpy as tp
import pims
import matplotlib.pyplot as plt
from .config_parser import get_detection_params, get_config
from .file_controller import FileController

# Initialize file controller (will be set by main application)
file_controller = None

def set_file_controller(controller):
    """Set the file controller instance."""
    global file_controller
    file_controller = controller


# =============================================================================
# TRACKPY WRAPPER FUNCTIONS
# =============================================================================

@pims.pipeline
def grayscale(frame):
    """Converts a frame to grayscale."""
    # This function is for use with pims pipelines, which expect RGB.
    # For single frames with OpenCV, use cv2.cvtColor.
    red = frame[:, :, 0]
    green = frame[:, :, 1]
    blue = frame[:, :, 2]
    return (1/3.0) * red + (1/3.0) * green + (1/3.0) * blue


def locate_particles(frame, feature_size=15, min_mass=100, invert=False, threshold=0):
    """
    Locates bright spots (particles) in a single grayscale frame.

    Parameters
    ----------
    frame : array
        A single grayscale frame from a video.
    feature_size : int, optional
        The approximate diameter of features to detect. Must be an odd integer.
    min_mass : float, optional
        The minimum integrated brightness of a feature.
    invert : bool, optional
        Set to True if looking for dark spots on a bright background.
    threshold : float, optional
        Clip band-passed data below this value.

    Returns
    -------
    pandas.DataFrame
        A DataFrame with the coordinates and other properties of the located particles.
    """
    located_features = tp.locate(
        frame,
        diameter=feature_size,
        minmass=min_mass,
        invert=invert,
        threshold=threshold
    )
    return located_features


def link_particles_to_trajectories(video_path, output_folder=None, params=None):
    """
    Main function to detect particles in all frames and link them into trajectories.
    
    Parameters
    ----------
    video_path : str
        Path to the video file to analyze
    output_folder : str, optional
        Folder to save trajectory data. If None, uses data folder from config.
    params : dict, optional
        Detection parameters. If None, reads from config.ini
        
    Returns
    -------
    pandas.DataFrame
        DataFrame with linked trajectories containing columns:
        - x, y: particle coordinates
        - frame: frame number
        - particle: trajectory ID
        - mass, size, ecc: particle properties
    """
    if params is None:
        params = get_detection_params()
    
    if output_folder is None:
        output_folder = file_controller.data_folder
    
    # Ensure output folder exists
    file_controller.ensure_folder_exists(output_folder)
    
    # Load video
    try:
        video = pims.Video(video_path)
    except Exception as e:
        print(f"Error loading video: {e}")
        return None
    
    print(f"Processing video with {len(video)} frames...")
    
    # Get detection parameters
    feature_size = int(params.get('feature_size', 15))
    min_mass = float(params.get('min_mass', 100.0))
    invert = bool(params.get('invert', False))
    threshold = float(params.get('threshold', 0.0))
    
    # Ensure odd feature size as required by trackpy
    if feature_size % 2 == 0:
        feature_size += 1
    
    # Step 1: Detect particles in all frames
    print("Detecting particles in all frames...")
    try:
        # Use trackpy's batch function for efficient processing
        particles = tp.batch(
            video, 
            diameter=feature_size, 
            minmass=min_mass, 
            invert=invert, 
            threshold=threshold,
            processes=1  # Use single process to avoid multiprocessing issues
        )
    except Exception as e:
        print(f"Error in particle detection: {e}")
        return None
    
    print(f"Found {len(particles)} particle detections across {particles['frame'].nunique()} frames")
    
    if len(particles) == 0:
        print("No particles detected!")
        return None
    
    # Step 2: Link particles into trajectories
    print("Linking particles into trajectories...")
    
    # Calculate search range based on expected particle speed
    # Assuming max speed of ~100 microns/second and typical fps
    fps = 30  # Default fps, could be extracted from video
    scaling = 1.0  # microns per pixel, could be from config
    max_speed_um_per_sec = 100
    search_range = int(np.ceil(max_speed_um_per_sec / (fps * scaling)))
    
    # Memory parameter: how many frames a particle can disappear and still be linked
    memory = 10
    
    try:
        trajectories = tp.link_df(
            particles, 
            search_range=search_range, 
            memory=memory
        )
    except Exception as e:
        print(f"Error in trajectory linking: {e}")
        return None
    
    print(f"Created {trajectories['particle'].nunique()} trajectories")
    
    # Step 3: Filter short trajectories
    min_trajectory_length = 10
    print(f"Filtering trajectories shorter than {min_trajectory_length} frames...")
    
    trajectories_filtered = tp.filter_stubs(trajectories, min_trajectory_length)
    
    print(f"After filtering: {trajectories_filtered['particle'].nunique()} trajectories")
    
    # Step 4: Drift subtraction (optional but recommended)
    print("Computing and subtracting drift...")
    try:
        # Compute drift
        drift = tp.compute_drift(trajectories_filtered, smoothing=15)
        
        # Subtract drift
        trajectories_final = tp.subtract_drift(trajectories_filtered, drift)
        trajectories_final = trajectories_final.reset_index(drop=True)
        
        print("Drift subtraction completed")
    except Exception as e:
        print(f"Warning: Drift subtraction failed: {e}")
        print("Using trajectories without drift subtraction")
        trajectories_final = trajectories_filtered
    
    # Step 5: Save results using FileController
    file_controller.save_trajectories_data(trajectories_final, "trajectories.csv")
    
    return trajectories_final


def analyze_trajectories(trajectories_df, scaling=1.0, fps=30):
    """
    Analyze linked trajectories to compute MSD and other metrics.
    
    Parameters
    ----------
    trajectories_df : pandas.DataFrame
        DataFrame with trajectory data from link_particles_to_trajectories
    scaling : float
        Microns per pixel
    fps : float
        Frames per second
        
    Returns
    -------
    dict
        Dictionary containing analysis results
    """
    if trajectories_df is None or len(trajectories_df) == 0:
        return None
    
    results = {}
    
    # Compute ensemble mean square displacement (eMSD)
    try:
        emsd = tp.emsd(trajectories_df, mpp=scaling, fps=fps, max_lagtime=100)
        results['emsd'] = emsd
        print("Computed ensemble MSD")
    except Exception as e:
        print(f"Error computing eMSD: {e}")
    
    # Compute individual MSD (iMSD) 
    try:
        imsd = tp.imsd(trajectories_df, mpp=scaling, fps=fps, max_lagtime=100)
        results['imsd'] = imsd
        print("Computed individual MSD")
    except Exception as e:
        print(f"Error computing iMSD: {e}")
    
    # Basic statistics
    results['num_trajectories'] = trajectories_df['particle'].nunique()
    results['num_frames'] = trajectories_df['frame'].nunique()
    results['total_detections'] = len(trajectories_df)
    
    # Trajectory lengths
    traj_lengths = trajectories_df.groupby('particle').size()
    results['mean_trajectory_length'] = traj_lengths.mean()
    results['std_trajectory_length'] = traj_lengths.std()
    
    print(f"Analysis complete:")
    print(f"  - {results['num_trajectories']} trajectories")
    print(f"  - {results['num_frames']} frames")
    print(f"  - Mean trajectory length: {results['mean_trajectory_length']:.1f} frames")
    
    return results


# =============================================================================
# PARTICLE PROCESSING FUNCTIONS
# =============================================================================

def find_and_save_errant_particles(image_paths, params=None, progress_callback=None):
    """
    Finds particles in a series of images and saves cropped images of the 5 most errant ones.

    Parameters
    ----------
    image_paths : list of str
        The paths to the image files.
    progress_callback : Signal, optional
        A signal to emit progress updates.
    """
    file_controller.delete_all_files_in_folder(file_controller.particles_folder)
    file_controller.ensure_folder_exists(file_controller.particles_folder)
    file_controller.ensure_folder_exists(file_controller.annotated_frames_folder)

    if params is None:
        params = get_detection_params()
    feature_size = int(params.get('feature_size', 15))
    min_mass = float(params.get('min_mass', 100.0))
    invert = bool(params.get('invert', False))
    threshold = float(params.get('threshold', 0.0))

    if feature_size % 2 == 0:
        feature_size += 1

    all_features = []
    original_images = {}

    for frame_idx, image_path in enumerate(image_paths):
        basename = os.path.basename(image_path)
        name_part = os.path.splitext(basename)[0]
        frame_number_str = name_part.split('_')[-1]
        frame_number = int(frame_number_str)

        if progress_callback:
            progress_callback.emit(f"Processing Frame {frame_number}")
        
        image = cv2.imread(image_path)
        if image is None:
            continue
        
        original_images[frame_idx] = image
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        features = locate_particles(
            gray_image,
            feature_size=feature_size,
            min_mass=min_mass,
            invert=invert,
            threshold=threshold
        )
        features['frame'] = frame_idx
        all_features.append(features)

        # Annotate and save frame
        if not features.empty:
            annotated_image = image.copy()
            for index, particle in features.iterrows():
                cv2.circle(annotated_image, (int(particle.x), int(particle.y)), int(feature_size/2) + 2, (0, 255, 255), 2)
            annotated_frame_path = os.path.join(file_controller.annotated_frames_folder, f"frame_{frame_number:05d}.jpg")
            cv2.imwrite(annotated_frame_path, annotated_image)

    if not all_features:
        if progress_callback:
            progress_callback.emit("No particles found.")
        return pd.DataFrame()

    combined_features = pd.concat(all_features, ignore_index=True)

    if not combined_features.empty:
        combined_features['mass_diff'] = combined_features['mass'] - min_mass
        top_5_mass_particles = combined_features.nsmallest(5, 'mass_diff')

        for i, particle in top_5_mass_particles.iterrows():
            frame_idx = int(particle['frame'])
            image_to_crop = original_images.get(frame_idx)
            if image_to_crop is None:
                continue

            x, y, size = particle['x'], particle['y'], particle['size']
            padding = 5
            half_size = (int(size) + padding) * 3
            x_min = max(0, int(x) - half_size)
            y_min = max(0, int(y) - half_size)
            x_max = min(image_to_crop.shape[1], int(x) + half_size)
            y_max = min(image_to_crop.shape[0], int(y) + half_size)

            particle_image = image_to_crop[y_min:y_max, x_min:x_max]

            center_x = int(x) - x_min
            center_y = int(y) - y_min
            cross_size = 5
            cv2.line(particle_image, (center_x - cross_size, center_y), (center_x + cross_size, center_y), (255, 255, 255), 1)
            cv2.line(particle_image, (center_x, center_y - cross_size), (center_x, center_y + cross_size), (255, 255, 255), 1)

            base_filename = f"mass_particle_{i}"
            particle_filename = os.path.join(file_controller.particles_folder, f"{base_filename}.png")
            cv2.imwrite(particle_filename, particle_image)

            mass_info_filename = os.path.join(file_controller.particles_folder, f"{base_filename}.txt")
            with open(mass_info_filename, 'w') as f:
                f.write(f"mass: {particle['mass']:.2f}\n")
                f.write(f"min_mass: {min_mass}\n")

        # Handle feature size difference
        combined_features['size_diff'] = abs(combined_features['size'] - feature_size)
        top_5_size_particles = combined_features.nlargest(5, 'size_diff')

        for i, particle in top_5_size_particles.iterrows():
            frame_idx = int(particle['frame'])
            image_to_crop = original_images.get(frame_idx)
            if image_to_crop is None:
                continue

            x, y, size = particle['x'], particle['y'], particle['size']
            padding = 5
            half_size = (int(size) + padding) * 3
            x_min = max(0, int(x) - half_size)
            y_min = max(0, int(y) - half_size)
            x_max = min(image_to_crop.shape[1], int(x) + half_size)
            y_max = min(image_to_crop.shape[0], int(y) + half_size)

            particle_image = image_to_crop[y_min:y_max, x_min:x_max]

            center_x = int(x) - x_min
            center_y = int(y) - y_min
            cross_size = 5
            cv2.line(particle_image, (center_x - cross_size, center_y), (center_x + cross_size, center_y), (255, 255, 255), 1)
            cv2.line(particle_image, (center_x, center_y - cross_size), (center_x, center_y + cross_size), (255, 255, 255), 1)

            base_filename = f"size_particle_{i}"
            particle_filename = os.path.join(file_controller.particles_folder, f"{base_filename}.png")
            cv2.imwrite(particle_filename, particle_image)

            size_info_filename = os.path.join(file_controller.particles_folder, f"{base_filename}.txt")
            with open(size_info_filename, 'w') as f:
                f.write(f"feature_size: {particle['size']:.2f}\n")
                f.write(f"parameter_feature_size: {feature_size}\n")

    if progress_callback:
        progress_callback.emit("Done.")

    return combined_features

def create_rb_gallery(trajectories_file, frames_folder=None, output_folder=None, 
                     search_range=None, memory=None, min_deviation_multiplier=None, max_displays=None):
    """
    Creates red-blue overlay images for the worst individual trajectory links.
    
    Parameters
    ----------
    trajectories_file : str
        Path to the CSV file containing trajectory data
    frames_folder : str, optional
        Path to the folder containing frame images. If None, uses file_controller.
    output_folder : str, optional
        Path to save the RB gallery images. If None, uses file_controller.rb_gallery_folder.
    search_range : float, optional
        Maximum expected jump distance for calculating deviations
    memory : int, optional
        Maximum expected memory (frames a particle can disappear)
    min_deviation_multiplier : float, optional
        DEPRECATED: No longer used. All worst links are shown regardless of threshold.
    max_displays : int, optional
        Maximum number of worst links to display (default 5)
    
    Key changes from previous version:
    - Scores individual frame-to-frame links instead of entire trajectories
    - Identifies the worst link in each trajectory
    - Always shows the top N worst links (no threshold filtering)
    - Displays the specific frame pair where the bad link occurred (not first/last)
    - Saves detailed metadata in .txt files explaining why each link is problematic
    """
    # Check if file_controller is available
    if file_controller is None:
        print("❌ ERROR: file_controller is not set! Cannot create RB gallery.")
        print("   Make sure particle_processing.set_file_controller() was called.")
        return
    
    if output_folder is None:
        output_folder = file_controller.rb_gallery_folder
    
    if frames_folder is None:
        frames_folder = file_controller.original_frames_folder
    
    print(f"📁 RB Gallery output folder: {output_folder}")
    print(f"📁 Frames folder: {frames_folder}")
    
    # Use FileController for folder management
    file_controller.ensure_folder_exists(output_folder)
    file_controller.delete_all_files_in_folder(output_folder)
    print(f"✅ Cleared RB gallery folder: {output_folder}")
    
    # Load trajectory data
    try:
        trajectories = pd.read_csv(trajectories_file)
    except Exception as e:
        print(f"Error loading trajectories: {e}")
        return
    
    if len(trajectories) == 0:
        print("No trajectory data found")
        return
    
    # Get linking parameters if not provided
    from .config_parser import get_linking_params
    linking_params = get_linking_params()
    if search_range is None:
        search_range = float(linking_params.get('search_range', 10))
    if memory is None:
        memory = int(linking_params.get('memory', 10))
    # max_displays defaults to 5 (show top 5 worst links)
    if max_displays is None:
        max_displays = int(linking_params.get('max_displays', 5))
    
    print(f"📊 Creating RB gallery with search_range={search_range}, memory={memory}")
    print(f"📊 Showing top {max_displays} worst trajectory links (no threshold filtering)")
    print(f"📊 Total trajectories: {trajectories['particle'].nunique()}")
    print(f"📊 Total trajectory points: {len(trajectories)}")
    
    # Score individual links instead of trajectories
    unique_particles = trajectories['particle'].unique()
    link_scores = []
    print(f"📊 Analyzing {len(unique_particles)} unique particles...")
    
    particles_with_links = 0
    particles_without_links = 0
    
    for particle_id in unique_particles:
        particle_data = trajectories[trajectories['particle'] == particle_id].sort_values('frame')
        
        if len(particle_data) < 2:
            particles_without_links += 1
            continue
        
        worst_link = None
        worst_score = float('-inf')  # Start with negative infinity to catch all scores
        
        num_links = len(particle_data) - 1
        if num_links == 0:
            continue
        
        for i in range(num_links):
            curr = particle_data.iloc[i]
            next_p = particle_data.iloc[i + 1]
            
            # Calculate jump distance
            dx = next_p['x'] - curr['x']
            dy = next_p['y'] - curr['y']
            jump_dist = np.sqrt(dx**2 + dy**2)
            
            # Calculate deviation from expected
            deviation = max(0, jump_dist - search_range)
            
            # Frame gap
            frame_gap = next_p['frame'] - curr['frame']
            
            # Score for this individual link
            # Higher score = worse link (more deviation from expected parameters)
            excess_gap = max(0, (frame_gap - 1) - memory) if frame_gap > 1 else 0
            link_score = (jump_dist - search_range) * 10 + deviation + excess_gap * 5
            
            # Skip if link_score is NaN or invalid
            if np.isnan(link_score) or not np.isfinite(link_score):
                continue
            
            # Track worst link in this trajectory (highest score = worst)
            if link_score > worst_score:
                worst_score = link_score
                worst_link = {
                    'particle_id': particle_id,
                    'score': link_score,
                    'jump_dist': jump_dist,
                    'deviation': deviation,
                    'frame_gap': frame_gap,
                    'frame_i': int(curr['frame']),
                    'frame_i1': int(next_p['frame']),
                    'x_i': curr['x'],
                    'y_i': curr['y'],
                    'x_i1': next_p['x'],
                    'y_i1': next_p['y'],
                    'data': particle_data
                }
        
        # Ensure worst_link is always set if we had links
        if num_links > 0 and worst_link is None:
            # This shouldn't happen, but handle edge case - use first link
            print(f"    ⚠️  WARNING: Particle {particle_id} had {num_links} links but worst_link is None! Using first link.")
            first_curr = particle_data.iloc[0]
            first_next = particle_data.iloc[1]
            dx = first_next['x'] - first_curr['x']
            dy = first_next['y'] - first_curr['y']
            jump_dist = np.sqrt(dx**2 + dy**2)
            deviation = max(0, jump_dist - search_range)
            frame_gap = first_next['frame'] - first_curr['frame']
            excess_gap = max(0, (frame_gap - 1) - memory) if frame_gap > 1 else 0
            link_score = (jump_dist - search_range) * 10 + deviation + excess_gap * 5
            worst_link = {
                'particle_id': particle_id,
                'score': link_score,
                'jump_dist': jump_dist,
                'deviation': deviation,
                'frame_gap': frame_gap,
                'frame_i': int(first_curr['frame']),
                'frame_i1': int(first_next['frame']),
                'x_i': first_curr['x'],
                'y_i': first_curr['y'],
                'x_i1': first_next['x'],
                'y_i1': first_next['y'],
                'data': particle_data
            }
        
        # Add worst link from this trajectory (no threshold filtering - we want all worst links)
        # worst_link should always be set if num_links > 0
        if worst_link is not None:
            link_scores.append(worst_link)
            particles_with_links += 1
        else:
            particles_without_links += 1
    
    print(f"📊 Particles with links added: {particles_with_links}")
    print(f"📊 Particles skipped (no valid links): {particles_without_links}")
    
    # Sort by score and take top N (always show worst ones)
    link_scores.sort(key=lambda x: x['score'], reverse=True)
    top_links = link_scores[:max_displays]
    
    print(f"📊 Total worst links found: {len(link_scores)}")
    print(f"📊 Selected {len(top_links)} worst trajectory links:")
    if len(top_links) == 0:
        print("   ⚠️  WARNING: No links found! Check if trajectories have at least 2 frames each.")
    else:
        for i, traj in enumerate(top_links):
            print(f"  {i+1}. Particle {traj['particle_id']}: score={traj['score']:.2f}, jump={traj['jump_dist']:.2f}, frames {traj['frame_i']}->{traj['frame_i1']}")
    
    crop_size = 100  # Size of the crop around each particle
    
    # Create RB overlay for each worst link showing the actual problem frames
    print(f"🖼️  Creating RB overlay images for {len(top_links)} links...")
    for idx, link_info in enumerate(top_links):
        particle_id = link_info['particle_id']
        frame_i = link_info['frame_i']
        frame_i1 = link_info['frame_i1']
        
        print(f"  [{idx+1}/{len(top_links)}] Processing particle {particle_id}, frames {frame_i}->{frame_i1}...")
        
        # Load the two frames where the bad link occurred
        # Construct filenames from frame numbers (not array indices)
        frame1_filename = os.path.join(frames_folder, f"frame_{frame_i:05d}.jpg")
        frame2_filename = os.path.join(frames_folder, f"frame_{frame_i1:05d}.jpg")
        
        try:
            frame1 = cv2.imread(frame1_filename)
            frame2 = cv2.imread(frame2_filename)
            
            if frame1 is None or frame2 is None:
                print(f"    ⚠️  Warning: Could not load frames {frame_i} or {frame_i1}")
                print(f"       Frame1 path: {frame1_filename} (exists: {os.path.exists(frame1_filename)})")
                print(f"       Frame2 path: {frame2_filename} (exists: {os.path.exists(frame2_filename)})")
                continue
            
            # Get particle positions at the problematic link
            x1, y1 = int(link_info['x_i']), int(link_info['y_i'])
            x2, y2 = int(link_info['x_i1']), int(link_info['y_i1'])
            
            # Calculate crop boundaries for frame1
            x1_min = max(0, x1 - crop_size // 2)
            y1_min = max(0, y1 - crop_size // 2)
            x1_max = min(frame1.shape[1], x1 + crop_size // 2)
            y1_max = min(frame1.shape[0], y1 + crop_size // 2)
            
            # Calculate crop boundaries for frame2
            x2_min = max(0, x2 - crop_size // 2)
            y2_min = max(0, y2 - crop_size // 2)
            x2_max = min(frame2.shape[1], x2 + crop_size // 2)
            y2_max = min(frame2.shape[0], y2 + crop_size // 2)
            
            # Crop the frames
            crop1 = frame1[y1_min:y1_max, x1_min:x1_max]
            crop2 = frame2[y2_min:y2_max, x2_min:x2_max]
            
            # Resize crops to same size
            target_size = (crop_size, crop_size)
            crop1 = cv2.resize(crop1, target_size)
            crop2 = cv2.resize(crop2, target_size)
            
            # Convert to grayscale for thresholding
            gray1 = cv2.cvtColor(crop1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(crop2, cv2.COLOR_BGR2GRAY)
            
            # Apply adaptive thresholding (Otsu's method)
            # First try with bright objects on dark background
            _, thresh1_bright = cv2.threshold(gray1, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            _, thresh2_bright = cv2.threshold(gray2, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Try with dark objects on bright background
            _, thresh1_dark = cv2.threshold(gray1, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            _, thresh2_dark = cv2.threshold(gray2, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            # Choose the thresholding that has better separation (higher variance)
            var1_bright = np.var(thresh1_bright)
            var1_dark = np.var(thresh1_dark)
            var2_bright = np.var(thresh2_bright)
            var2_dark = np.var(thresh2_dark)
            
            # Choose thresholding that better separates particles
            thresh1 = thresh1_dark if var1_dark > var1_bright else thresh1_bright
            thresh2 = thresh2_dark if var2_dark > var2_bright else thresh2_bright
            
            # Ensure particles are white (255) - invert if needed
            white_pixels1 = np.sum(thresh1 == 255)
            white_pixels2 = np.sum(thresh2 == 255)
            
            # If less than 30% are white, assume we need to invert
            if white_pixels1 < (thresh1.size * 0.3):
                thresh1 = cv2.bitwise_not(thresh1)
            if white_pixels2 < (thresh2.size * 0.3):
                thresh2 = cv2.bitwise_not(thresh2)
            
            # Create RGB overlay with white background
            # Background is white (255, 255, 255), particles are red (frame1) or blue (frame2)
            rb_overlay = np.ones((crop_size, crop_size, 3), dtype=np.uint8) * 255  # White background
            
            # Apply thresholded particles as red (frame1) and blue (frame2)
            # Where thresh1 is white (255), make it red
            red_mask = thresh1 == 255
            rb_overlay[red_mask, 0] = 255  # Red channel
            rb_overlay[red_mask, 1] = 0
            rb_overlay[red_mask, 2] = 0
            
            # Where thresh2 is white (255), make it blue
            blue_mask = thresh2 == 255
            rb_overlay[blue_mask, 0] = 0
            rb_overlay[blue_mask, 1] = 0
            rb_overlay[blue_mask, 2] = 255  # Blue channel
            
            # Where both are present, create purple overlay
            both_mask = red_mask & blue_mask
            rb_overlay[both_mask, 0] = 255  # Red channel
            rb_overlay[both_mask, 1] = 0
            rb_overlay[both_mask, 2] = 255  # Blue channel (makes purple)
            
            # Draw particle centers as small white circles
            center = crop_size // 2
            cv2.circle(rb_overlay, (center, center), 3, (255, 255, 255), -1)
            
            # Add frame information text
            cv2.putText(rb_overlay, f'F{frame_i}', (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
            cv2.putText(rb_overlay, f'F{frame_i1}', (5, crop_size - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
            
            # Save the RB overlay image
            base_filename = f"particle_{particle_id}_link_{frame_i}_to_{frame_i1}"
            output_filename = os.path.join(output_folder, f"{base_filename}_rb_overlay.png")
            success = cv2.imwrite(output_filename, rb_overlay)
            if success:
                print(f"    ✅ Saved RB overlay: {output_filename}")
            else:
                print(f"    ❌ Failed to save RB overlay: {output_filename}")
            
            # Determine why this link is bad
            issues = []
            if link_info['jump_dist'] > search_range:
                excess = link_info['jump_dist'] - search_range
                issues.append(f"Jump distance ({link_info['jump_dist']:.2f} px) exceeds search_range ({search_range} px) by {excess:.2f} px")
            else:
                issues.append(f"Jump distance ({link_info['jump_dist']:.2f} px) is within search_range ({search_range} px)")
            
            if link_info['frame_gap'] > 1:
                gap_violations = link_info['frame_gap'] - 1  # Frames the particle disappeared
                if gap_violations > memory:
                    excess_gap = gap_violations - memory
                    issues.append(f"Frame gap ({link_info['frame_gap']} frames, {gap_violations} disappearances) exceeds memory ({memory} frames) by {excess_gap} frames")
                else:
                    issues.append(f"Frame gap ({link_info['frame_gap']} frames, {gap_violations} disappearances) is within memory ({memory} frames)")
            else:
                issues.append(f"No frame gap (consecutive frames)")
            
            # Save metadata with detailed information
            metadata_text = f"""PARTICLE ID: {link_info['particle_id']}
FRAME TRANSITION: {frame_i} → {frame_i+1}

PARAMETER VIOLATIONS:
{chr(10).join(issues)}

METRICS:
Jump Distance: {link_info['jump_dist']:.2f} pixels
Search Range: {search_range} pixels
Deviation: {link_info['deviation']:.2f} pixels (jump_distance - search_range)
Frame Gap: {link_info['frame_gap']} frames
Memory: {memory} frames
Link Score: {link_info['score']:.2f} (higher = worse)"""
            
            # Save .txt file
            metadata_filename = os.path.join(output_folder, f"{base_filename}.txt")
            try:
                with open(metadata_filename, 'w') as f:
                    f.write(metadata_text)
                print(f"    ✅ Saved metadata: {metadata_filename}")
            except Exception as e:
                print(f"    ❌ Failed to save metadata: {e}")
            
        except Exception as e:
            import traceback
            print(f"    ❌ Error processing particle {particle_id} link: {e}")
            traceback.print_exc()
            continue
    
    print(f"✅ RB gallery created in: {output_folder}")
    print(f"✅ Processed {len(top_links)} worst trajectory links")
    if len(top_links) == 0:
        print(f"⚠️  No trajectory links found (need at least 2 frames per particle)")
    else:
        print(f"✅ Created {len(top_links)} RB overlay images with metadata files")
        print(f"   Showing the {len(top_links)} worst links ranked by deviation score")


if __name__ == '__main__':
    # Example usage
    video_path = "path/to/your/video.avi"
    trajectories = link_particles_to_trajectories(video_path)
    
    if trajectories is not None:
        analysis = analyze_trajectories(trajectories)
        print("Trajectory linking and analysis complete!")
    else:
        print("Trajectory linking failed!")
