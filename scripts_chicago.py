__author__ = "Jerome Thai"
__email__ = "jerome.thai@berkeley.edu"

'''
Various scripts for processing data
'''

import numpy as np
from process_data import extract_features, process_links, geojson_link, \
    process_trips, process_net, process_node, array_to_trips, process_results
from metrics import average_cost, cost_ratio, cost, save_metrics
from frank_wolfe import solver, solver_2, solver_3
from heterogeneous_solver import gauss_seidel, jacobi
from All_Or_Nothing import all_or_nothing


def process_chicago_network():
    '''
    prepare .csv files for our algorithm from .txt files available in
    http://www.bgu.ac.il/~bargera/tntp/
    '''
    process_trips('data/ChicagoSketch_trips.txt', 'data/Chicago_od.csv')
    process_net('data/ChicagoSketch_net.txt', 'data/Chicago_net.csv')
    input = 'data/ChicagoSketch_node.csv'
    output = 'data/Chicago_node.csv'
    max_X = -87.110063
    min_X = -88.9242653
    max_Y = 42.711908
    min_Y = 40.946233
    process_node(input, output, min_X, max_X, min_Y, max_Y)


def load_chicago():
    net = np.loadtxt('data/Chicago_net.csv', delimiter=',', skiprows=1)
    demand = np.loadtxt('data/Chicago_od.csv', delimiter=',', skiprows=1)
    node = np.loadtxt('data/Chicago_node.csv', delimiter=',', skiprows=1)
    geometry = extract_features('data/ChicagoSketch_net.txt')
    return net, demand, node, geometry


def capacities_of_chicago():
    '''
    visualize capacities in the network of Chicago
    '''
    net, demand, node, features = load_chicago()
    links = process_links(net, node, features)
    color = features[:,0] / 2000. # we choose the capacity
    geojson_link(links, ['capacity', 'length', 'fftt'], color)


def multiply_demand_by_2():
    '''
    Multiply demand in Chicago by 2 and generate input file for Bar-Gera
    '''
    demand = np.loadtxt('data/Chicago_od.csv', delimiter=',', skiprows=1)
    demand[:,2] = 2.*demand[:,2]
    array_to_trips(demand, 'data/ChicagoSketch_trips_2.txt')


def results_for_chicago():
    '''
    Take Bar-gera results and check the link flows are aligned with Chicago_net.csv
    '''
    process_results('data/Chicago_raw_results_2.csv', 'data/Chicago_results_2.csv',\
        'data/Chicago_net.csv')


def frank_wolfe_on_chicago():
    '''
    Frank-Wolfe on Chicago with the inputs processed from:
    http://www.bgu.ac.il/~bargera/tntp/
    '''
    graph, demand, node, features = load_chicago()
    results = np.loadtxt('data/Chicago_results.csv', delimiter=',', skiprows=1)     
    demand[:,2] = demand[:,2] / 4000
    f = solver(graph, demand, max_iter=1000, display=1)
    # error: 0.00647753330249, time: 664.151s
    # f = solver_2(graph, demand, max_iter=1000, q=100, display=1)
    # error: 0.00646125552755, time: 664.678s
    # f = solver_3(graph, demand, max_iter=1000, q=200, display=1)
    # error: 0.00648532089623, time: 665.074s
    print np.linalg.norm(f*4000 - results[:,2]) / np.linalg.norm(results[:,2])


def frank_wolfe_on_chicago_2():
    '''
    Frank-Wolfe on Chicago with the inputs processed from:
    http://www.bgu.ac.il/~bargera/tntp/
    but we multiply the demand by 2 to have more congestion
    '''    
    graph, demand, node, features = load_chicago()
    results = np.loadtxt('data/Chicago_results_2.csv', delimiter=',') 
    demand[:,2] = demand[:,2] / 2000 # technically, it's 2*demand/4000
    # f = solver(graph, demand, max_iter=1000, display=1, stop=1e-2)
    # f = solver_2(graph, demand, max_iter=1000, q=100, display=1, stop=1e-2)
    f = solver_3(graph, demand, max_iter=1000, q=50, display=1, stop=1e-2)
    print np.linalg.norm(f*4000 - results) / np.linalg.norm(results)
    print average_cost(f, graph, demand)


def visualize_equilibrium_in_chicago():
    '''
    visualize costs in the network of Chicago
    '''
    net, demand, node, f = load_chicago()
    flow = np.loadtxt('data/Chicago_results_2.csv', delimiter=',')
    # flow = np.loadtxt('data/Chicago_results.csv', delimiter=',', skiprows=1)[:,2]
    print average_cost(flow/4000., net)
    costs = cost_ratio(flow/4000., net)
    features = np.zeros((f.shape[0],4))
    features[:,:3] = f
    features[:,3] = costs
    links = process_links(net, node, features)
    color = features[:,3] - 1.0 # we choose the costs
    geojson_link(links, ['capacity', 'length', 'fftt', 'tt_over_fftt'], color)


def heterogeneous_demand(d, alpha):
    d_nr = np.copy(d)
    d_r = np.copy(d)
    d_nr[:,2] = (1-alpha) * d_nr[:,2]
    d_r[:,2] = alpha * d_r[:,2]
    return d_nr, d_r


def add_cognitive_cost(net, feat, thres, cog_cost):
    net2 = np.copy(net)
    small_capacity = np.zeros((net2.shape[0],))
    for row in range(net2.shape[0]):
        if feat[row,0] < thres:
            small_capacity[row] = 1.0
            net2[row,3] = net2[row,3] + cog_cost
    return net2, small_capacity


def multiply_cognitive_cost(net, feat, thres, cog_cost):
    net2 = np.copy(net)
    small_capacity = np.zeros((net2.shape[0],))
    for row in range(net2.shape[0]):
        if feat[row,0] < thres:
            small_capacity[row] = 1.0
            net2[row,3:] = net2[row,3:] * cog_cost
    return net2, small_capacity


def chicago_ratio_r_nr():
    '''
    study the test_*.csv files generated by chicago_parametric_study()
    in particular, visualize the ratio each type of users on each link
    '''
    fs = np.loadtxt('data/test_3.csv', delimiter=',', skiprows=0)
    ratio = np.divide(fs[:,0], np.maximum(np.sum(fs, axis=1), 1e-8))
    net, demand, node, geometry = load_chicago()
    features = np.zeros((fs.shape[0], 4))
    features[:,:3] = geometry
    features[:,3] = ratio
    links = process_links(net, node, features)
    color = 5. * ratio # we choose the ratios of nr over r+nr
    geojson_link(links, ['capacity', 'length', 'fftt', 'r_non_routed'], color)


def chicago_tt_over_fftt():
    '''
    study the test_*.csv files generated by chicago_parametric_study()
    visualize tt/fftt for each edge
    '''
    net, demand, node, geometry = load_chicago()
    g_nr, small_capacity = add_cognitive_cost(net, geometry, 2000., 1000.)
    # f = np.loadtxt('data/test_0.csv', delimiter=',', skiprows=0)
    alpha = 0.01
    fs = np.loadtxt('data/test_{}.csv'.format(int(100.*alpha)), delimiter=',', skiprows=0)
    # f = np.loadtxt('data/test_100.csv', delimiter=',', skiprows=0)
    f = np.sum(fs, axis=1)
    costs = cost_ratio(f, net)
    features = np.zeros((f.shape[0], 4))
    features[:,:3] = geometry
    features[:,3] = costs
    links = process_links(net, node, features)
    color = (costs - 1.0) * 2.0 + 1.0
    geojson_link(links, ['capacity', 'length', 'fftt', 'tt_over_fftt'], color)


def chicago_flow_over_capacity():
    '''
    study the test_*.csv files generated by chicago_parametric_study()
    visualize flow/calacity for each edge
    '''
    net, demand, node, geometry = load_chicago()
    # f = np.loadtxt('data/test_1.csv', delimiter=',', skiprows=0)
    fs = np.loadtxt('data/test_2.csv', delimiter=',', skiprows=0)
    # fs = np.loadtxt('data/test_3.csv', delimiter=',', skiprows=0)
    # fs = np.loadtxt('data/test_4.csv', delimiter=',', skiprows=0)
    # f = np.loadtxt('data/test_5.csv', delimiter=',', skiprows=0)
    f = np.sum(fs, axis=1)
    features = np.zeros((f.shape[0], 4))
    features[:,:3] = geometry
    f = np.divide(f, features[:,0]/4000.0)
    features[:,3] = f
    links = process_links(net, node, features)
    color = 2.0*f + 1.0
    geojson_link(links, ['capacity', 'length', 'fftt', 'flow_over_capacity'], color)


def chicago_parametric_study_2(alpha):
    '''
    study the test_*.csv files generated by chicago_parametric_study()
    in particular, display the average costs for each type of users
    alpha = 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0
    '''
    # graphs
    g_r, d, node, feat = load_chicago()
    # g_nr, small_capacity = add_cognitive_cost(g_r, feat, 2000., 1000.)
    g_nr, small_capacity = multiply_cognitive_cost(g_r, feat, 2000., 1000.)
    d[:,2] = d[:,2] / 2000 # technically, it's 2*demand/4000

    if alpha == 0.0:
        print 'non-routed = 1.0, routed = 0.0'
        fs = solver_3(g_nr, d, max_iter=1000, q=100, display=1, stop=1e-2)    
        np.savetxt('data/test_0.csv', fs, delimiter=',')
        return

    if alpha == 1.0:
        print 'non-routed = 0.0, routed = 1.0'
        fs = solver_3(g_r, d, max_iter=1000, q=100, display=1, stop=1e-2)    
        np.savetxt('data/test_100.csv', fs, delimiter=',')
        return

    print 'non-routed = {}, routed = {}'.format(1-alpha, alpha)
    d_nr, d_r = heterogeneous_demand(d, alpha)
    fs = gauss_seidel([g_nr,g_r], [d_nr,d_r], solver_3, max_iter=1000, display=1,\
        stop=1e-2, q=50, stop_cycle=1e-3)
    np.savetxt('data/test_{}.csv'.format(int(alpha*100)), fs, delimiter=',')


def chicago_metrics(alphas):
    '''
    study the test_*.csv files generated by chicago_parametric_study()
    in particular, display the average costs for each type of users
    alpha = 0.0, 0.25, 0.5, 0.75, 1.0
    '''
    out = np.zeros((len(alphas),6))
    net, d, node, features = load_chicago()
    d[:,2] = d[:,2] / 2000. # technically, it's 2*demand/4000
    net2, small_capacity = multiply_cognitive_cost(net, features, 2000., 100.)
    save_metrics(alphas, net, net2, d, features, small_capacity, 'data/test_{}.csv', \
        'data/out.csv')


def chicago_gas_emissions():
    net, d, node, feat = load_chicago()
    alpha = .01
    fs = np.loadtxt('data/test_{}.csv'.format(int(alpha*100)), delimiter=',')
    speed = 60.0 * np.divide(feat[:,1], np.maximum(cost(np.sum(fs, axis=1), net), 10e-8))
    features = np.zeros((fs.shape[0], 5))
    features[:,:3] = feat
    features[:,3] = np.minimum(speed, 80.)
    co2 = gas_emission(speed)
    features[:,4] = co2
    links = process_links(net, node, features)
    # color = speed / 15.
    color = (co2<=350.) + np.multiply((co2>350.), 1.0+(co2-350.)/150.)
    geojson_link(links, ['capacity', 'length', 'fftt', 'speed', 'co2'], color)


def main():
    # process_chicago_network()
    # capacities_of_chicago()
    # visualize_equilibrium_in_chicago()
    # multiply_demand_by_2()
    # results_for_chicago()
    # frank_wolfe_on_chicago()
    # frank_wolfe_on_chicago_2()
    # chicago_parametric_study()
    # chicago_ratio_r_nr()
    # chicago_tt_over_fftt()
    # chicago_flow_over_capacity()
    # chicago_parametric_study_2(1.0)
    chicago_metrics([.0,.1,.2,.3,.4,.5,.6,.7,.8,.9,1.0])


if __name__ == '__main__':
    main()
