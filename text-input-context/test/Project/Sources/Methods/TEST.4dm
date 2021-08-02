//%attributes = {}
C_COLLECTION:C1488($colSources)
$colSources:=Input sources list   //OK

ARRAY TEXT:C222($sources;0)
_o_INPUT SOURCES LIST ($sources)  //OK

$source:=_o_Get input source   //OK

$objSsource:=Get input source   //OK

ARRAY TEXT:C222($locales;1)
$locales{1}:=ALL ROMAN INPUT SOURCES
SET INPUT SOURCE LOCALES ($locales)  //limit to ascii

ARRAY TEXT:C222($locales;0)
SET INPUT SOURCE LOCALES ($locales)  //any locale