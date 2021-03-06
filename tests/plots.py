from nego.mediated.Agents_Supervisor import NegoModel
from nego.bilateral.Agents_Supervisor import NegoModel
import matplotlib.pyplot as plt
import pandas as pd
import csv

#### LOG ####
N = 100
model = NegoModel(N)
timestep = 3
for i in range(timestep):
    m=model.perception()
    decisions = model.decision_fct()
    rewards = model.feedback()
    perceptions = model.perception()
    model.create_agents(m,decisions,rewards)
    model.step(decisions,rewards,perceptions,timestep)
    model.log().to_csv("out_log["+str(i+1)+"].csv",index=False)

#### PLOT ####
with open('out_log['+str(timestep)+'].csv', newline='') as csvfile:
    reader = csv.reader(csvfile,delimiter=',', quotechar='|')
    label = []
    y = []
    x = []
    for row in reader:
        if row[1] != 'id':
            label_row = row[5]
            production = row[2]
            id = row[1]
            y.append(production)
            x.append(id)
            label.append(label_row)
    colors = ['red' if l == "buyer" else 'green' for l in label]
    plt.scatter(x,y,color=colors)
    plt.legend(bbox_to_anchor=(1, 1), bbox_transform=plt.gcf().transFigure)
    plt.show()

#### TEST THE EVALUATION ####
s=NegoModel(5)
s.threshold=3
measures_poor = s.evaluate([1,0,0,0,0],0)
measures_uniform = s.evaluate([1,1,1,0,0],0)
measures_rich = s.evaluate([1,1,1,1,1],0)

x = ["1_poor","2_uniform","3_rich"]

y_gini = [measures_poor["gini"],measures_uniform["gini"],measures_rich["gini"]]
plt.plot(x,y_gini,label="gini")

y_success = [measures_poor["success"],measures_uniform["success"],measures_rich["success"]]
plt.plot(x,y_success,label="success")

y_efficiency = [measures_poor["efficiency"], measures_uniform["efficiency"], measures_rich["efficiency"]]
plt.plot(x,y_efficiency,label="efficiency")

plt.legend(bbox_to_anchor=(1, 1), bbox_transform=plt.gcf().transFigure)
plt.show()