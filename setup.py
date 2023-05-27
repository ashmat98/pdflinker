from setuptools import setup

setup(
   name='pdflinker',
   version='0.2.0',
   author='Ashot Matevosyan',
   author_email='ashmat98@gmail.com',
   packages=['pdflinker', 'pdflinker.resources'],
   scripts=['bin/pdflinker', 'bin/pdflinkergui'],
   description='An awesome package that does something',
   long_description=open('README.md').read(),
   long_description_content_type="text/markdown",
   install_requires=[
    "fitz", "tk"
   ],
)