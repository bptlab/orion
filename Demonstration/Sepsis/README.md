# Demonstration of Orion on the Sepsis Event Log

This page demonstrates orion by analyzing the [Sepsis](https://data.4tu.nl/articles/dataset/Sepsis_Cases_-_Event_Log/12707639) event log. This event log is especially appropriate for change pattern analysis, as it includes two measurement activities (CRP and Leucocytes). We will demonstrate, how orion can be used to retrieve novel insights from Sepsis. A detailed case study can also be found [here](https://github.com/bptlab/Context-Aware-Change-Pattern-Detection), where we also discuss the meaning of the results.

## Main Page

After uploading the event log, the user arrives at the main page to perform the data-preprocessing and analysis steps described in the paper. On the left hand side, a discovered process model is displayed. On the right hand side, a navigation bar is present, which give access to the featurees of orion.

|![alt text](https://github.com/bptlab/orion/blob/master/Demonstration/Sepsis/Images/landing_page.PNG)|
|:--:| 
| *Orion Main Page after uploading the event log* |

## Detect Dynamic Event Attributes

The detection of dynamic event attributes is done automatically. However, additional classification of dynamic event attributes is required, as the change detection needs to separate between continuous and categorical event attributes. We implemented a heuristic for that, which requires a user-defined threshold. We allow the user to set that and edit the classification, if a misclassification took place. This is shown in the image below, where the slider determines the threshold and the attributes can be clicked to switch the attribute classification.

|![alt text](https://github.com/bptlab/orion/blob/master/Demonstration/Sepsis/Images/Detect_DEA.JPG)|
|:--:| 
| *Dynamic Event Attribute Detection Page*
