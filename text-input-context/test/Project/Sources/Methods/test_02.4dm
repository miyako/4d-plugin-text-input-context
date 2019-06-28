//%attributes = {"preemptive":"capable"}
  //test: thread safe, arrays

ARRAY TEXT:C222($sources_tt;0)
_o_INPUT SOURCES LIST ($sources_tt)

ALERT:C41(String:C10(Size of array:C274($sources_tt)))

ARRAY TEXT:C222($locales_tt;0)
GET INPUT SOURCE LOCALES ($locales_tt)

ALERT:C41(String:C10(Size of array:C274($locales_tt)))