## Installation
```
pip install .
```

## Example usage

We generatef a pdf file from `sample.tex` file, however, the hyperlinks are turned off (by default). We apply our tool on it by the following command:

```
pdflinker -p  "example/sample.pdf" \
--pattern '(D)' -a right \
--pattern '[D]' -a end 
```
and this will create the file `example/sample (with links).pdf`.