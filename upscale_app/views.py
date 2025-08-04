from django.conf import settings
from django.shortcuts import render
from .forms import UploadImageForm
import os
import uuid
from PIL import Image
from gradio_client import Client

def index(request):
    upscaled_url = original_url = None
    display_width = display_height = None
    # Add these so the template doesn't error out if they aren't set
    original_width = original_height = upscaled_width = upscaled_height = None 
    error = None

    # Use the 'index_new.html' template
    template_name = 'upscale_app/index_new.html' 

    if request.method == 'POST':
        form = UploadImageForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data['image']
            
            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
            ext = os.path.splitext(uploaded_file.name)[1].lower() if uploaded_file.name else '.png'
            filename = f"{uuid.uuid4()}{ext}"
            input_path = os.path.join(settings.MEDIA_ROOT, filename)

            with open(input_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            original_url = settings.MEDIA_URL + filename
            
            try:
                with Image.open(input_path) as img:
                    original_width, original_height = img.size
            except Exception as e:
                print(f"Could not read original image dimensions: {e}")

            try:
                # IMPORTANT: Replace with YOUR Space name
                client = Client("inevitable-gs/image-upscaler") 
                
                # CORRECTED: Pass input_path as a positional argument
                result_filepath, status_message = client.predict(
                    input_path,
                    api_name="/predict"
                )

                if status_message != "Success":
                    raise Exception(f"API returned an error: {status_message}")

                output_filename = f"upscaled_{filename}"
                output_path_local = os.path.join(settings.MEDIA_ROOT, output_filename)
                
                os.rename(result_filepath, output_path_local)

                upscaled_url = settings.MEDIA_URL + output_filename
                
                try:
                    with Image.open(output_path_local) as img:
                        upscaled_width, upscaled_height = img.size
                except Exception as e:
                    print(f"Could not read upscaled image dimensions: {e}")

            except Exception as e:
                error = f"Failed to process image with the API. Is your Hugging Face Space running? Error: {e}"
                print(error)
                if os.path.exists(input_path):
                     os.remove(input_path)
                original_url = None

    else:
        form = UploadImageForm()

    return render(request, template_name, {
        'form': form,
        'original': original_url,
        'upscaled': upscaled_url,
        'original_width': original_width,
        'original_height': original_height,
        'upscaled_width': upscaled_width,
        'upscaled_height': upscaled_height,
        'error': error
    })