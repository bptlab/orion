# Demonstration of Orion on the Sepsis Event Log

This page demonstrates orion by analyzing the [Sepsis](https://data.4tu.nl/articles/dataset/Sepsis_Cases_-_Event_Log/12707639) event log. This event log is especially appropriate for change pattern analysis, as it includes two measurement activities (CRP and Leucocytes). We will demonstrate, how orion can be used to retrieve novel insights from Sepsis. A detailed case study can also be found [here](https://github.com/bptlab/Context-Aware-Change-Pattern-Detection), where we also discuss the meaning of the results.

## Main Page

After uploading the event log, the user arrives at the main page to perform the data-preprocessing and analysis steps described in the paper. On the left hand side, a discovered process model is displayed. On the right hand side, a navigation bar is present, which give access to the features of orion.

|![alt text](https://github.com/bptlab/orion/blob/master/Demonstration/Sepsis/Images/landing_page.PNG)|
|:--:| 
| *Orion Main Page after uploading the event log* |

## Detect Dynamic Event Attributes

The detection of dynamic event attributes is done automatically. However, additional classification of dynamic event attributes is required, as the change detection needs to separate between continuous and categorical event attributes. We implemented a heuristic for that, which requires a user-defined threshold. We allow the user to set that and edit the classification, if a misclassification took place. This is shown in the image below, where the slider determines the threshold and the attributes can be clicked to switch the attribute classification. A detailed description of the deteciton algorithms and the user-defined threshold can be found in the respective paper [1].

|![alt text](https://github.com/bptlab/orion/blob/master/Demonstration/Sepsis/Images/Detect_DEA.JPG)|
|:--:| 
| *Dynamic Event Attribute Detection Page* |


## Apply Context-Aware Activitiy Transformation

This feature is especially useful for Sepsis, as the measurement activities (CRP and Leucocytes) are recurring activities in the event log. This features allows to put these activities into their respective context, which is before or after other activities. A detailed description can be found again in the respective paper [2]. First, recurring activities can be selected based on a repetition score, which is shown behind the activity names.

|![alt text](https://github.com/bptlab/orion/blob/master/Demonstration/Sepsis/Images/Context_1.JPG)|
|:--:| 
| *Context-Aware Activity Transformation: Selection of recurring activities* |

After the selection of recurring activities (in this case CRP, Leucocytes, and LacticAcid), the user needs to choose how the activities should be transformed. Again, we provide a threshold to determine that semi-automatically, which is the bar at the top. Below, the activities are shown, which will be the context for each recurring activity. For example, CRP will be tranformed to "CRP BEFORE Release A", "CRP BEFORE Release B",... and "CRP AFTER ER Sepsis Triage", "CRP AFTER Admission NC", and "CRP AFTER Admission IC". Hitting the Transform button performs the activity transformation and returns to the main page.

|![alt text](https://github.com/bptlab/orion/blob/master/Demonstration/Sepsis/Images/Context_2.JPG)|
|:--:| 
| *Context-Aware Activity Transformation: Selection of context for recurring activities* |

The transformed process model with a path filter of 0.2 is illustrated below.

|![alt text](https://github.com/bptlab/orion/blob/master/Demonstration/Sepsis/Images/Context_PM.JPG)|
|:--:| 
| *Context-Aware Activity Transformation: Transformed Sepsis Process Model* |

## Detect Change Patterns and Relationships between Change Patterns

These two steps do not need any user interaction, which take around 5 minutes in total for Sepsis. What happens in the background can be read in the respective papers [3,4]. Please be aware, that the activities in the Spesis event log only contain one dynamic event attribute. Thus, no relationships between change patterns can be identified. 

## Explore Change Patterns

This is the exploration part of the tool. To explore detected change patterns, we implemented a heatmap, which illustrates slices of the OLAP cube, storing all change patterns. The figure below illustrates an example heatmap with change patterns detected in the transformed Sepsis event log. 

The heatmap is dynamically configurable, such that the user can define what should be shown on the respective x-, y-, and z-axis. The example shows event attributes on the x-axis and relations (in this case eventually follows relations) on the y-axis. Further, either continuous or categorical event attributes can be displayed due to their differen effect sizes. Coloured cells in the heatmap show statistical significant change patterns with their respective effect size. When hovering over cells, more details are displayed, such as the p-value, change in mean values, and sample size.

|![alt text](https://github.com/bptlab/orion/blob/master/Demonstration/Sepsis/Images/Matrix.PNG)|
|:--:| 
| *Heatmap for change pattern exploration* |

When clicking on one cell in the heatmap, the respective cell can be analysed in more detail. The figure below shows a histogram of the selected change pattern with its change pattern value differences (the difference of the event atttribute values in the selected relation). As the effect size of -0.9 indicates, most values are decreasing from "CRP AFTER Admission IC" to "CRP BEFORE Release A".



|![alt text](https://github.com/bptlab/orion/blob/master/Demonstration/Sepsis/Images/Hist.JPG)|
|:--:| 
| *Histogram of selected change pattern* |

Further, one can illustrate selected change patterns in the process model. The process model below visualizes two change patterns. One in the eventually folows relation from "CRP AFTER ER Sepsis Triage" to "CRP AFTER Admission NC" with a positive effect size of 0.35, indicating a value increase. This is visualized by a dotted line, indicating the eventually follows relation, which is coloured in red, as the value increases. The numbers at the edges represent the average value of the event attribute in the relation. The second change pattern is a value decrease from "CRP AFTER Admission NC" to "CRP BEFORE Release A", visualized by a dotted line in blue.

|![alt text](https://github.com/bptlab/orion/blob/master/Demonstration/Sepsis/Images/final_pm.JPG)|
|:--:| 
| *Process model enhanced with change patterns in CRP* |


## References

[1] Cremerius, J., Weske, M.: Supporting domain data selection in data-enhanced process models. In: Wirtschaftsinformatik 2022 Proceedings 3 (2022)


[2] Cremerius, J., Weske, M.: Context-aware change pattern detection in event attributes of recurring activities. In: Cabanillas, C., Perez, F. (eds.) Intelligent Information Systems. pp. 1–8. Springer International Publishing, Cham (2023)


[3] Cremerius, J., Weske, M.: Change detection in dynamic event attributes. In: Di Ciccio, C., Dijkman, R., del R ́ıo Ortega, A., Rinderle-Ma, S. (eds.) Business Process Management Forum. pp. 157–172. Springer International Publishing, Cham (2022)


[4] Cremerius, J., Weske, M.: Relationships between change patterns in dynamic event attributes. In: Business Process Management Workshops (accepted, not published). Springer International Publishing (2023)
