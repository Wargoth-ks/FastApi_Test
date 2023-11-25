import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, status
from source.conf.configs import settings


class Cloudinary:
    
    def __init__(self, settings=settings):
        
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True
        )

    def upload_image(self, upload_file, username):
        
        dest = f"fast_api_users/{username}"
        image = cloudinary.uploader.upload(
            upload_file, 
            public_id=dest, 
            overwrite=True,
            width=250, 
            height=250,
            gravity="face",
            radius="max",
            crop="fill",
            timeout=3
            )
        image_url = cloudinary.CloudinaryImage(dest).build_url(
            width=250, 
            height=250,
            gravity="face",
            radius="max",
            crop="fill", 
            version=image.get('version')
            )
        return image_url
            
    def delete_image(self, username):
        
        dest = f"fast_api_users/{username}"
        
        if dest is None:
            raise HTTPException(
            status_code=status.HTTP_404, detail="Image not found"
        )
        image_delete = cloudinary.uploader.destroy(public_id=dest, timeout=3)
        
        return image_delete
    
    
cloud = Cloudinary()