from sklearn.svm import SVC
from sklearn.grid_search import GridSearchCV
import numpy as np


def trainNewModel(features):
    X = np.array( features*2 ).reshape(-1,128)
    y = np.array( range(0,len(features))*2 ).reshape(-1,)

    print np.shape(X), np.shape(y)
    param_grid = [
            {'C': [1, 10, 100, 1000],
             'kernel': ['linear']},
            {'C': [1, 10, 100, 1000],
             'gamma': [0.001, 0.0001],
             'kernel': ['rbf']}
        ]
    clf = GridSearchCV(SVC(C=1, probability=True), param_grid, cv=2)
    #clf = SVC(probability=True)
    try:
        clf.fit(X,y)
        return clf
    except Exception as ex:
        print ex
        return None

def predict(vec, model):
    return model.predict_proba(vec)
