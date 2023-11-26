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
            secure=True,
        )

    def upload_image(self, upload_file, username):
        """
        The upload_image function takes in a file and username, uploads the image to cloudinary,
        and returns the url of the uploaded image. The function uses Cloudinary's API to upload
        the image with specific parameters: public_id is set as fast_api_users/{username}, which
        is where all user profile images are stored on Cloudinary; overwrite=True ensures that if an
        image already exists for this user it will be overwritten;
        width and height are both set to 250px; gravity="face";
        ensures that any faces detected in the photo will be centered within a 250x250 square frame.
        The radius is set to "max" and the crop mode is set to "fill" to ensure the image 
        fits within the square frame.
        The function also sets a timeout of 3 seconds for the upload operation.

        After the image is uploaded, the function builds the image url 
        using the CloudinaryImage's build_url method.
        The url is built with the same parameters used for the upload (width, height, gravity, radius, crop),
        and also includes the version of the image obtained from the upload response.

        """

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
            timeout=3,
        )
        image_url = cloudinary.CloudinaryImage(dest).build_url(
            width=250,
            height=250,
            gravity="face",
            radius="max",
            crop="fill",
            version=image.get("version"),
        )
        return image_url

    def delete_image(self, username):
        """
        The delete_image function deletes an image from the cloudinary server.
            Args:
                username (str): The username of the user whose profile picture is to be deleted.

        :param self: Represent the instance of the class
        :param username: Identify the image to be deleted
        :return: A dictionary with the following keys:
        """

        dest = f"fast_api_users/{username}"

        if dest is None:
            raise HTTPException(status_code=status.HTTP_404, detail="Image not found")
        image_delete = cloudinary.uploader.destroy(public_id=dest, timeout=3)

        return image_delete


cloud = Cloudinary()
