from setuptools import setup

setup(
   name='pdflinker',
   version='0.1.0',
   author='Ashot Matevosyan',
   author_email='ashmat98@gmail.com',
   packages=['pdflinker'],
   scripts=['bin/pdflinker'],
   description='An awesome package that does something',
   long_description=open('README.txt').read(),
   long_description_content_type="text/markdown",
   install_requires=[
    "fitz"
   ],
)