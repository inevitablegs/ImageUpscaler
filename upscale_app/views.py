import os
import uuid
from django.conf import settings
from django.shortcuts import render
from .forms import UploadImageForm
import subprocess
from PIL import Image

def upscale_image(input_path, output_path):
    try:
        # Get absolute paths to all required files
        executable_path = os.path.join(settings.BASE_DIR, 'realesrgan-ncnn-vulkan')
        model_path = os.path.join(settings.BASE_DIR, 'models')
        
        # Verify all files exist
        required_files = [
            executable_path,
            os.path.join(model_path, 'realesrgan-x4plus.param'),
            os.path.join(model_path, 'realesrgan-x4plus.bin')
        ]
        
        for file in required_files:
            if not os.path.exists(file):
                raise FileNotFoundError(f"Required file not found: {file}")

        result = subprocess.run([
            executable_path,
            '-i', input_path,
            '-o', output_path,
            '-n', 'realesrgan-x4plus',
            '-m', model_path,
            '-g', '-1'  # Use NVIDIA GPU (change to 0 for AMD or -1 for CPU)
        ], check=True, capture_output=True, text=True)
        
        print("Upscaling output:", result.stdout)
        if result.stderr:
            print("Upscaling errors:", result.stderr)
            
        return os.path.exists(output_path)
        
    except subprocess.CalledProcessError as e:
        print(f"Upscaling failed with error: {e}")
        print("Command output:", e.stdout)
        print("Command error:", e.stderr)
        return False
    except Exception as e:
        print(f"Unexpected error during upscaling: {e}")
        return False

def index(request):
    upscaled_url = original_url = None
    display_width = display_height = None  # These will control the display size
    error = None

    if request.method == 'POST':
        form = UploadImageForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data['image']
            
            # Ensure media directory exists
            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
            
            # Generate unique filename
            ext = os.path.splitext(uploaded_file.name)[1].lower()
            filename = f"{uuid.uuid4()}{ext}"
            input_path = os.path.join(settings.MEDIA_ROOT, filename)
            output_filename = f"upscaled_{filename}"
            output_path = os.path.join(settings.MEDIA_ROOT, output_filename)

            # Save the uploaded image
            with open(input_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            if os.path.exists(input_path):
                try:
                    # Get original dimensions
                    with Image.open(input_path) as img:
                        original_width, original_height = img.size
                    
                    # Calculate display size (limit to 600px on the longest side)
                    max_display_size = 600
                    if original_width > original_height:
                        display_width = min(original_width, max_display_size)
                        display_height = int((original_height/original_width) * display_width)
                    else:
                        display_height = min(original_height, max_display_size)
                        display_width = int((original_width/original_height) * display_height)
                    
                    # Upscale the image
                    if upscale_image(input_path, output_path):
                        original_url = settings.MEDIA_URL + filename
                        upscaled_url = settings.MEDIA_URL + output_filename
                    else:
                        error = "Failed to upscale the image."
                except Exception as e:
                    error = f"Error processing image: {str(e)}"
                    if os.path.exists(input_path):
                        os.remove(input_path)
            else:
                error = "Failed to save uploaded image."
    else:
        form = UploadImageForm()

    return render(request, 'upscale_app/index.html', {
        'form': form,
        'original': original_url,
        'upscaled': upscaled_url,
        'display_width': display_width,
        'display_height': display_height,
        'error': error
    })