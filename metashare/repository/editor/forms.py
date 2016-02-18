import logging

from xml.etree.ElementTree import fromstring

from django import forms
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from metashare.storage.models import ALLOWED_ARCHIVE_EXTENSIONS
from metashare.settings import LOG_HANDLER, MAXIMUM_UPLOAD_SIZE
from zipfile import is_zipfile
import subprocess
from metashare.settings import ROOT_PATH
from os.path import dirname
# Setup logging support.
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(LOG_HANDLER)



def _validate_resource_data(value):
    """
    Validates that the uploaded resource data is valid.
    """
    if value.size > MAXIMUM_UPLOAD_SIZE:
        raise ValidationError('The maximum upload file size is {:.3} ' \
          'MB!'.format(float(MAXIMUM_UPLOAD_SIZE)/(1024*1024)))
    
    _valid_extension = False
    for _allowed_extension in ALLOWED_ARCHIVE_EXTENSIONS:
        if value.name.lower().endswith(_allowed_extension):
            _valid_extension = True
            break
    
    if not _valid_extension:
        raise ValidationError('Invalid upload file type. Valid file types ' \
          'are: {}'.format(ALLOWED_ARCHIVE_EXTENSIONS))
    
    return value


def _validate_resource_description(value):
    """
    Validates that the uploaded resource description is valid.
    """
    filename = value.name.lower()
    if filename.endswith('.xml'):
        _xml_raw = ''
        for _chunk in value.chunks():
            _xml_raw += _chunk
        try:
            _xml_tree = fromstring(_xml_raw)

        except Exception, _msg:
            raise ValidationError(_msg)
        schema_validate_xml(_xml_raw)
    elif filename.endswith('.zip'):
        valid = False
        try:
            valid = is_zipfile(value)
            value.seek(0)
        except:
            valid = False
        if not valid:
            raise ValidationError('File is not a zip file.') 
    else:
        raise ValidationError('Invalid upload file type. XML or ZIP file required.')
    
    
    # For the moment, we simply pass through the received value.  Later, we
    # could run an XML validation script here or perform other checks...
    return value

#MILTOS
def schema_validate_xml(value):
    command=[]
    path = '{0}/'.format((dirname(ROOT_PATH)))
    command.append('java')
    command.append('-jar')
    command.append('{}xmlValidator_schema1.1/schemaValidator.jar'.format(path))
    command.append('{}misc/schema/ELRC-SHARE/META-SHARE-Resource.xsd'.format(path))
    value = value.replace('\r','').replace('\n','').replace('\t','')
    command.append(value)

    p = subprocess.Popen(command,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    _msg = p.communicate()[0]
    if not _msg == "\nPassed\n":
        raise ValidationError(mark_safe('<b>Schema Validation</b><br/> {}'.format(_msg)))
    return value

class StorageObjectUploadForm(forms.Form):
    """
    Form to upload resource data into a StorageObject instance.
    """
    resource = forms.FileField(label="Resource",
      help_text="You can upload resource data (<={:.3} MB) using this " \
      "widget. Note that this will overwrite the current data!".format(
        float(MAXIMUM_UPLOAD_SIZE/(1024*1024))),
      validators=[_validate_resource_data])

    uploadTerms = forms.BooleanField(label="Upload Terms",
      help_text="By clicking this checkbox, you confirm that you have " \
      "cleared permissions for the file you intend to upload.")

class ResourceDescriptionUploadForm(forms.Form):
    """
    Form to upload a resource description into the Django database.
    """
    description = forms.FileField(label="Resource Description(s)",
      help_text="You can upload a new resource description in XML format, " \
      "or many resource descriptions in a ZIP file containing XML files. " \
      "Please make sure the XML files are Schema-valid before proceeding.",
      validators=[_validate_resource_description])

    uploadTerms = forms.BooleanField(label="Upload Terms",
      help_text="By clicking this checkbox, you confirm that you have " \
      "cleared permissions for the description(s) you intend to upload.")

