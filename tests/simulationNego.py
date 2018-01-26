import functools
import itertools
import pandas as pd
import numpy as np
from nego.src.Decisions import NegoDecisionLogicAgent
from nego.src.Decisions import NegoDecisionLogic
from nego.src.RewardLogic import NegoRewardLogic
from nego.src.MeasurementGen import NegoMeasurementGen
from nego.src.Evaluation import  NegoEvaluationLogic
from nego.src.utilsnego import *
from nego.src.Agent import *
from nego.src.Supervisor import *
import csv

def run_experiment(test,conf):
    log_tot=[]
    for r in range(conf["reps"]):
        for idx,p in expandgrid(conf["params"]).iterrows():
            params=p.to_dict()
            params.update({"repetition":r})
            f=functools.partial(conf["meas_fct"],**params)
            model=BaseSupervisor(N=int(params["N"]),measurement_fct=f,
                                 decision_fct=conf["dec_fct"],
                                 agent_decision_fct=conf["dec_fct_agent"],
                                 reward_fct=conf["rew_fct"],
                                 evaluation_fct=conf["eval_fct"],
                                 agent_type=NegoAgent)
            model.run(conf["T"],params=params)
            log_tot=log_tot+model.log # concatenate lists
    #print(log_tot)
    # compute statistics for all tables in log file
    varnames=[k for k,v in conf["params"].items() if len(v)>1] # keep vars for which there is more than one value
    for varname in varnames:
        stats_rew=get_stats(log_tot,"reward",idx=[varname])
        stats_perc=get_stats(log_tot,"perception",idx=[varname],cols=["production","consumption","tariff"])
        stats_decs=get_stats(log_tot,"decisions",idx=[varname],cols=["action","cost"])
        stats_eval=get_stats(log_tot,"evaluation",idx=[varname],cols=["social_welfare","gini","success","efficiency"])
        plot_trend(stats_rew,varname,"./rewards_"+str(test)+"_"+str(varname)+"_nego.png")
        plot_trend(stats_perc,varname,"./perceptions_"+str(test)+"_"+str(varname)+"_nego.png")
        plot_trend(stats_decs,varname,"./decisions_"+str(test)+"_"+str(varname)+"_nego.png")
        plot_measures(stats_eval,varname,"./eval_"+str(test)+"_"+str(varname)+"_nego.png")

class RewardLogicFull(NegoRewardLogic):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.benefit=5
        self.damage=-10

    def get_rewards(self,decisions):
        """
        Almost full contribution is required
        """
        percs=np.sum([p["value"] for p in self.model.current_state["perception"]])
        thresh=np.random.uniform(percs*0.8,percs) # almost full contrib
        contribs=np.sum([d["contribution"] for d in decisions])
        outcome=success_nego(thresh,np.sum(contribs))
        if outcome==1:
            costs=np.array([d["cost"] for d in decisions])
            ret=-costs+self.benefit
            ret=[{"reward":r} for r in ret]
        else:
            ret=[{"reward":self.damage}]*self.model.N
        return ret

class RewardLogicUniform(NegoRewardLogic):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.benefit=5
        self.damage=-10

    def get_rewards(self,decisions):
        """
        The threshold is randomly generated around the average contribution
        """
        percs=[p["production"] for p in self.model.current_state["perception"]]
        thresh=np.random.normal(loc=np.mean(percs),scale=1)
        thresh=max(1,thresh)
        contribs=np.sum([d["contribution"] for d in decisions])
        # if thresh<=contribs:
        #     print("success "+str(thresh)+" "+str(contribs))
        # else:
        #     print("insuccess "+str(thresh)+" "+str(contribs))
        outcome=success_nego(thresh,np.sum(contribs))
        if outcome==1:
            costs=np.array([d["cost"] for d in decisions])
            ret=-costs+self.benefit
            ret=[{"reward":r} for r in ret]
        else:
            ret=[{"reward":self.damage}]*self.model.N
        return ret

class DecisionLogicEmpty(NegoDecisionLogic):
    """
    Returns a constant decision
    """
    def get_decision(self,perceptions):
        pass

    def get_feedback(self,perceptions,reward):
        pass

class DecisionLogicSupervisorMandatory(NegoDecisionLogic):
    """
    Returns a constant decision
    """
    def get_decision(self,perceptions):
        self.last_actions=[{"contribution":a["value"],"cost":a["cost"],"agentID":a["agentID"],
                            "contributed":True,"timestep":a["timestep"]} for a in perceptions]
        return self.last_actions

class DecisionLogicSupervisorProbabilistic(NegoDecisionLogic):
    """
    Returns a constant decision
    """
    def get_decision(self,perceptions):
        self.last_actions=[{"contribution":a["value"],"cost":a["cost"],"agentID":a["agentID"],
                            "contributed":(True if np.random.uniform()<=0.5 else False),"timestep":a["timestep"]}
                           for a in perceptions]
        return self.last_actions

class MeasurementGenUniform(NegoMeasurementGen):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.n1=kwargs["n1"]
        self.n2=kwargs["n2"]

    def get_measurements(self,population,timestep):
        """
        Returns a list of dictionaries containing the measurements: the state of each agent at the current timestep
        """
        ret=[{"value":np.random.uniform(self.n1,self.n2),"cost":0,"timestep":timestep,"agentID":i}
             for i in range(len(population))]
        return ret

class MeasurementGenNormal(NegoMeasurementGen):
    def __init__(self,*args, **kwargs):
        super().__init__()
        self.mu=kwargs["mu"]
        self.s=3

    def get_measurements(self,population,timestep):
        """
        Returns a list of dictionaries containing the measurements: the state of each agent at the current timestep
        """
        ret=[{"production":np.random.normal(loc=self.mu,scale=self.s),
              "consumption":np.random.normal(loc=self.mu,scale=self.s),
              "timestep":timestep,"agentID":i,"tariff":np.random.uniform(low=0,high=5)}
             for i in range(len(population))]
        return ret

class MeasurementGenBinomial(NegoMeasurementGen):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.mu1=kwargs["mu1"]
        self.s1=1
        self.mu2=kwargs["mu2"]
        self.s2=1
        self.produce_low = kwargs["buy_low"] # proportion of agents who can produce in lower caste
        self.produce_high = kwargs["buy_high"] # proportion of agents who can produce in higher caste
        self.caste=kwargs["low_caste"] # proportion of agents in low caste
        self.biased_low=kwargs["bias_low"]  # proportion of biased agents among low caste
        self.biased_high = kwargs["bias_high"] # proportion of biased agents among low caste

    def get_measurements(self,population,timestep):
        """
        Returns a list of dictionaries containing the measurements: the state of each agent at the current timestep
        """
        #TODO add this in run_experiment to make it more general and applicable for all classes
        with open('tariff.csv') as csvfile:
            has_header = csv.Sniffer().sniff(csvfile.readline())
            csvfile.seek(0)
            readCSV = csv.DictReader(csvfile)
            if has_header:
                next(readCSV)
            data = [row for row in readCSV]
            tariff = data[timestep]["inrpriceperkwh"]
            tariff_new = abs(np.random.normal(loc=float(tariff),scale=self.s2))
            production = np.random.uniform(20000,100000)*8/24/20000
            ret=[{"consumption":(np.random.normal(loc=self.mu2,scale=self.s1)
                           if i>len(population)*self.caste else
                           np.random.normal(loc=self.mu1,scale=self.s2)),
                  "tariff":tariff_new,
                  "social_type":(2 if i>len(population)*self.caste else 1),
                  "production":((0 if i>len(population)*self.caste*self.produce_high else production)
                                if i>len(population)*self.caste else
                                (0 if i>len(population)*self.caste*self.produce_low else production)),
                  "biased":((0 if i>len(population)*self.caste*self.biased_high else 1)
                            if i>len(population)*self.caste else
                            (0 if i>len(population)*self.caste*self.biased_low else 1)),
                  "cost":0,"timestep":timestep,"agentID":i}  # high class is 2, low class is 1
                 for i in range(len(population))]
            return ret

if __name__ == '__main__':
    # tests={"uniform":{"N":10,"rep":10,"params":{"mu":[5,20,50]},"meas_fct":MeasurementGenNormal},
    #        "binomial":{"N":10,"rep":10,"params":{"mu1":[1],"mu2":[5,20,50],
    #                    "meas_fct":MeasurementGenBinomial}}
    # tests={"uniform":{"N":10,"rep":1,"params":{"mu":[2,5,8]},"meas_fct":MeasurementGenNormal}}
    tests={"binomial":{"T":23,"reps":50,"dec_fct":NegoDecisionLogic,"dec_fct_agent":NegoDecisionLogicAgent,
                       "rew_fct":NegoRewardLogic, "eval_fct":NegoEvaluationLogic,
                       "params":{"N":[20,50,100],"mu1":[1.01],"mu2":[1.37],"bias_low":[0.5],
                                 "bias_high":[0.2,0.5,0.8],"low_caste":[0.36,0.5,0.8],
                                 "buy_low":[0.25],"buy_high":[0.48]},
                       "meas_fct":MeasurementGenBinomial}}
    for test,conf in tests.items():
        run_experiment(test,conf)