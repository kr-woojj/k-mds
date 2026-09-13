| Provider 필드 | IMO ID | FAL50 명칭 | 형식 | 규칙 | 비고 |
|---|---|---|---|---|---|
| airTemp | IMO0628 | Air temperature | n..3,1 | CODEBOOK_1_1 |  |
| avgShaftRevSlr | IMO0617 | Speed propeller | n..4,1 | CODEBOOK_1_1 |  |
| avgShipSpeedSlr | IMO0333 | Speed over ground | n..4,1 | CODEBOOK_1_1 |  |
| ballastQuantity | IMO0452 | Total ballast water on board | n..16,6 | CODEBOOK_1_1 |  |
| beaufortScale | IMO0625 | Wind force | n..2 | CODEBOOK_1_1 |  |
| berthName | IMO0548 | Berth, coded | To be defined | MOST_SPECIFIC | candidates=['IMO0548', 'IMO0758'] |
| consumptionBlrDo | IMO0673 | Fuel consumed, by Auxiliary Boiler | n..4,1 | FUEL_TYPE_STRUCTURE | IMO0654=MDO occurrence |
| consumptionBlrHfo | IMO0673 | Fuel consumed, by Auxiliary Boiler | n..4,1 | FUEL_TYPE_STRUCTURE | IMO0654=HFO occurrence |
| consumptionBlrLsfo | IMO0673 | Fuel consumed, by Auxiliary Boiler | n..4,1 | FUEL_TYPE_STRUCTURE | IMO0654=VLSFO2020 occurrence |
| consumptionBlrMgo | IMO0673 | Fuel consumed, by Auxiliary Boiler | n..4,1 | FUEL_TYPE_STRUCTURE | IMO0654=MGO occurrence |
| consumptionBlrUlsfo | IMO0673 | Fuel consumed, by Auxiliary Boiler | n..4,1 | FUEL_TYPE_STRUCTURE | IMO0654=ULSFO2020 occurrence |
| consumptionBlrUlsmgo | IMO0673 | Fuel consumed, by Auxiliary Boiler | n..4,1 | FUEL_TYPE_STRUCTURE | IMO0654=ULSMGO2020 occurrence |
| consumptionGeDo | IMO0893 | Fuel consumed, by Auxiliary Engine | n..4,1 | FUEL_TYPE_STRUCTURE | IMO0654=MDO occurrence |
| consumptionGeHfo | IMO0893 | Fuel consumed, by Auxiliary Engine | n..4,1 | FUEL_TYPE_STRUCTURE | IMO0654=HFO occurrence |
| consumptionGeLsfo | IMO0893 | Fuel consumed, by Auxiliary Engine | n..4,1 | FUEL_TYPE_STRUCTURE | IMO0654=VLSFO2020 occurrence |
| consumptionGeMgo | IMO0893 | Fuel consumed, by Auxiliary Engine | n..4,1 | FUEL_TYPE_STRUCTURE | IMO0654=MGO occurrence |
| consumptionGeUlsfo | IMO0893 | Fuel consumed, by Auxiliary Engine | n..4,1 | FUEL_TYPE_STRUCTURE | IMO0654=ULSFO2020 occurrence |
| consumptionGeUlsmgo | IMO0893 | Fuel consumed, by Auxiliary Engine | n..4,1 | FUEL_TYPE_STRUCTURE | IMO0654=ULSMGO2020 occurrence |
| consumptionMeDo | IMO0670 | Fuel consumed, by Main Engine | n..4,1 | FUEL_TYPE_STRUCTURE | IMO0654=MDO occurrence |
| consumptionMeHfo | IMO0670 | Fuel consumed, by Main Engine | n..4,1 | FUEL_TYPE_STRUCTURE | IMO0654=HFO occurrence |
| consumptionMeLsfo | IMO0670 | Fuel consumed, by Main Engine | n..4,1 | FUEL_TYPE_STRUCTURE | IMO0654=VLSFO2020 occurrence |
| consumptionMeMgo | IMO0670 | Fuel consumed, by Main Engine | n..4,1 | FUEL_TYPE_STRUCTURE | IMO0654=MGO occurrence |
| consumptionMeUlsfo | IMO0670 | Fuel consumed, by Main Engine | n..4,1 | FUEL_TYPE_STRUCTURE | IMO0654=ULSFO2020 occurrence |
| consumptionMeUlsmgo | IMO0670 | Fuel consumed, by Main Engine | n..4,1 | FUEL_TYPE_STRUCTURE | IMO0654=ULSMGO2020 occurrence |
| consumptionMecylOil | IMO0678 | Cylinder lube oil, consumption | n..4,1 | CODEBOOK_1_1 |  |
| consumptionMelscylOil | IMO0678 | Cylinder lube oil, consumption | n..4,1 | CODEBOOK_1_1 |  |
| consumptionOtherDo | IMO0903 | Fuel consumed, by Other Fuel Consuming Devices | n..4,1 | FUEL_TYPE_STRUCTURE | IMO0654=MDO occurrence |
| consumptionOtherHfo | IMO0903 | Fuel consumed, by Other Fuel Consuming Devices | n..4,1 | FUEL_TYPE_STRUCTURE | IMO0654=HFO occurrence |
| consumptionOtherLsfo | IMO0903 | Fuel consumed, by Other Fuel Consuming Devices | n..4,1 | FUEL_TYPE_STRUCTURE | IMO0654=VLSFO2020 occurrence |
| consumptionOtherMgo | IMO0903 | Fuel consumed, by Other Fuel Consuming Devices | n..4,1 | FUEL_TYPE_STRUCTURE | IMO0654=MGO occurrence |
| consumptionOtherUlsfo | IMO0903 | Fuel consumed, by Other Fuel Consuming Devices | n..4,1 | FUEL_TYPE_STRUCTURE | IMO0654=ULSFO2020 occurrence |
| consumptionOtherUlsmgo | IMO0903 | Fuel consumed, by Other Fuel Consuming Devices | n..4,1 | FUEL_TYPE_STRUCTURE | IMO0654=ULSMGO2020 occurrence |
| dateEventUtc | IMO0065 | Date and time of departure - actual | an..35 | EVENT_CONTEXT | eventName=Departure S/By |
| distanceToGo | IMO0615 | Distance to next port | n..4,1 | MOST_SPECIFIC | candidates=['IMO0537', 'IMO0615'] |
| draftAft | IMO0622 | Draught aft | n..4,2 | MOST_SPECIFIC | candidates=['IMO0357', 'IMO0622'] |
| draftFore | IMO0621 | Draught forward | n..4,2 | MOST_SPECIFIC | candidates=['IMO0357', 'IMO0621'] |
| draftMid | IMO0357 | Ship draught | n..2,2 | CODEBOOK_1_1 |  |
| etb | IMO0541 | Date and time to location in port - estimated | an..35 | CODEBOOK_1_1 |  |
| etd | IMO0066 | Date and time of departure - estimated | an..35 | CODEBOOK_1_1 |  |
| eventKey | IMO0597 | Event type, coded | an..4 | MOST_SPECIFIC | candidates=['IMO0597', 'IMO0598'] |
| freshWaterConsumed | IMO0641 | Fresh water consumed | n..16,6 | CODEBOOK_1_1 |  |
| freshWaterProduced | IMO0640 | Fresh water produced | n..16,6 | CODEBOOK_1_1 |  |
| freshWaterSupplied | IMO0639 | Fresh water bunkered | n..16,6 | CODEBOOK_1_1 |  |
| hourSlr | IMO0600 | Elapsed time | n..16,6 | CODEBOOK_1_1 |  |
| isEuPort | — |  |  | AMBIGUOUS | candidates=['IMO0856', 'IMO0857'] |
| legNo | IMO0605 | Voyage leg identifier | an..35 | CODEBOOK_1_1 |  |
| nextPortCode | IMO0084 | Next port of call, coded | an5 | CODEBOOK_1_1 |  |
| nextPortEtaLtc | IMO0543 | Date and time to location in port - planned | an..35 | CODEBOOK_1_1 |  |
| nextPortEtaUtc | IMO0064 | Date and time of arrival - estimated | an..35 | CODEBOOK_1_1 |  |
| nextPortName | IMO0085 | Next port of call name | an..256 | CODEBOOK_1_1 |  |
| portCode | IMO0111 | Port of departure, coded | an5 | EVENT_CONTEXT | eventName=Departure S/By |
| portName | IMO0112 | Port of departure name | an..256 | EVENT_CONTEXT | eventName=Departure S/By |
| positionLat | IMO0601 | Ship position when reporting, latitude | an..10 | MOST_SPECIFIC | candidates=['IMO0233', 'IMO0544', 'IMO0601'] |
| positionLon | IMO0602 | Ship position when reporting, longitude | an..11 | MOST_SPECIFIC | candidates=['IMO0233', 'IMO0545', 'IMO0602'] |
| relWindDirection | IMO0626 | Wind direction, estimated, relative | n..3,1 | CODEBOOK_1_1 |  |
| robDo | IMO0674 | Fuel quantity remaining onboard | n..4,1 | CODEBOOK_1_1 |  |
| robFreshWater | IMO0645 | Fresh water remaining onboard | n..16,6 | CODEBOOK_1_1 |  |
| robGecylOil | IMO0676 | Cylinder lube oil remaining onboard | n..4,1 | CODEBOOK_1_1 |  |
| robHfo | IMO0674 | Fuel quantity remaining onboard | n..4,1 | CODEBOOK_1_1 |  |
| robLsfo | IMO0674 | Fuel quantity remaining onboard | n..4,1 | CODEBOOK_1_1 |  |
| robMecylOil | IMO0676 | Cylinder lube oil remaining onboard | n..4,1 | CODEBOOK_1_1 |  |
| robMelscylOil | IMO0676 | Cylinder lube oil remaining onboard | n..4,1 | CODEBOOK_1_1 |  |
| robMgo | IMO0674 | Fuel quantity remaining onboard | n..4,1 | CODEBOOK_1_1 |  |
| robUlsfo | IMO0674 | Fuel quantity remaining onboard | n..4,1 | CODEBOOK_1_1 |  |
| robUlsmgo | IMO0674 | Fuel quantity remaining onboard | n..4,1 | CODEBOOK_1_1 |  |
| shipCourse | IMO0332 | Course over ground | n..4,1 | MOST_SPECIFIC | candidates=['IMO0332', 'IMO0620'] |
| steamingDistanceSlr | IMO0613 | Distance over ground | n..4,1 | CODEBOOK_1_1 |  |
| trueWindDirection | IMO0627 | Wind direction, estimated, true | n..3,1 | MOST_SPECIFIC | candidates=['IMO0360', 'IMO0627'] |
| voyNo | IMO0191 | Voyage number | an..17 | CODEBOOK_1_1 |  |
| waveDirection | IMO0631 | Sea direction, true | n..3 | CODEBOOK_1_1 |  |
| waveHeight | IMO0632 | Sea height | n..2 | CODEBOOK_1_1 |  |