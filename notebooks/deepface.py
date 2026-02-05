from deepface import DeepFace
import os

# Configuration
DB_PATH = "face_database"
os.makedirs(DB_PATH, exist_ok=True)

# ==================== REGISTER A FACE ====================
def register_face(image_path, person_name):
    """Register a new face in the database"""
    # Create person folder
    person_folder = os.path.join(DB_PATH, person_name)
    os.makedirs(person_folder, exist_ok=True)
    
    # Copy/save the image
    import shutil
    dest_path = os.path.join(person_folder, f"{person_name}.jpg")
    shutil.copy(image_path, dest_path)
    
    print(f"✓ Registered {person_name}")
    return dest_path

# ==================== RECOGNIZE A FACE ====================
def recognize_face(image_path, threshold=0.6):
    """Find matching face in database"""
    try:
        # Search for face in database
        results = DeepFace.find(
            img_path=image_path,
            db_path=DB_PATH,
            model_name="Facenet512",  # or "VGG-Face", "ArcFace"
            distance_metric="cosine",
            enforce_detection=True
        )
        
        if len(results) > 0 and len(results[0]) > 0:
            # Get best match
            match = results[0].iloc[0]
            distance = match['distance']
            identity = match['identity']
            
            # Extract person name from path
            person_name = os.path.basename(os.path.dirname(identity))
            
            if distance < threshold:
                print(f"✓ Match found: {person_name} (distance: {distance:.3f})")
                return person_name, distance
            else:
                print(f"✗ No match (closest: {person_name}, distance: {distance:.3f})")
                return None, distance
        else:
            print("✗ No faces found in database")
            return None, None
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return None, None

# ==================== USAGE ====================

# Register some faces
register_face("person1.jpg", "John")
register_face("person2.jpg", "Sarah")
register_face("person3.jpg", "Mike")

# Recognize a face
person, confidence = recognize_face("test_face.jpg")

if person:
    print(f"\n🎯 Identified as: {person}")
else:
    print("\n❌ Unknown person")