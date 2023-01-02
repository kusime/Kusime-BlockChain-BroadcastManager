import time
from flask import Flask, jsonify, request
# cors fix
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)


@app.route('/alive', methods=["GET", "POST"])
def alive():
    if request.method == 'GET':
        return "alive", 200
    post = request.get_json()
    print("Body=>", post)
    return jsonify(post), 200

# get all active nodes from NodeManager


def get_activate_node():
    MAX_RETRIES = 5
    for retry in range(MAX_RETRIES):
        try:
            # register the node
            response = requests.get(
                f'{NODE_MANAGER}/get-nodes')
            print(response.text)
            if response.status_code == 200:
                # registration successful, return True
                return response.json()["nodes"]

        except:
            # catch exceptions raised by requests library
            print(
                f"BroadcastManager : NODE_MANAGER {NODE_MANAGER} => Get All nodes failed {retry+1}/{MAX_RETRIES}")
            # retry the request after a short delay
            time.sleep(1)
    else:
        # if we exit the loop without a break, registration failed
        print("Failed to get nodes information from the NodeManager")
        return False


def node_alive_check(nodes):
    print("\n---------Node Alive Check ----------")
    checked_alive_node = []
    for node in nodes:
        try:
            response = requests.get(
                f'http://{node}/alive', timeout=1)
            if response.status_code == 200:
                print(f"{node} ==> alive")
                checked_alive_node.append(node)
        except:
            # this node seems to be dead
            # notice the NodeManager
            print(f"{node} seems already dead , noticing the NodeManager")
            try:
                response = requests.post(
                    f'{NODE_MANAGER}/check-node', json={
                        "sus_node": node,
                        # use fast_death to notice the NodeManager do not wait too much time
                        "fast_death": True
                    }, timeout=0.5)
            except:
                print("Successfully notice NodeManager")
    print("\n---------Node Alive Check ----------")
    return checked_alive_node

# will have no responsible for all the incoming requests but forwards them to all the requests they know about


def get_activate_node_rsa_public_key(node):
    try:
        print("Getting public key from NodeManager...")
        # register the node
        response = requests.post(
            f'{NODE_MANAGER}/get-node-pub', json={
                "query_node": node
            })
        if response.status_code == 200:
            # registration successful, return True
            return response.json()["pub_key"]
    except:
        print("Failed to get the rsa_pub_key from the NodeManager")
        return None


@app.route('/broadcast', methods=["POST"])
def broadcast():
    """
        Security Layer :
            src_node_id check ,
            peer alive check ,
            peer node dead notice,
        payload should have signature field , however , the broadcast will not care about it.
        Rule:
            req :  {"src_node_id":"localhost:5000",endpoint:"/broadcast/transaction" , "payload"}
            resp : {"src_node_public_key":"rsa_pub_key...",
                "payload":{"signature"}}


    """
    broadcast_info = request.get_json()
    # unpacking the broadcast info
    try:
        broadcast_src_node_id = broadcast_info["src_node_id"]
        broadcast_endpoint = broadcast_info["endpoint"]
        broadcast_payload = broadcast_info.get("payload", None)
    except:
        api_return = {
            "message": "Missing required field"
        }
        print("")
        return jsonify(api_return), 400

    # get all available nodes
    may_active_nodes = get_activate_node()
    if may_active_nodes == False:
        # get node information failed
        api_return = {
            "message": "Nodes information get failed, NodeManager offline ,broadcast failed"
        }
        print(
            "BroadcastManager: Failed to get may_active_nodes information from NodeManager")
        return jsonify(api_return), 500

    print(may_active_nodes)
    # NOTE: security check
    if broadcast_src_node_id not in may_active_nodes:
        # get node information failed
        api_return = {
            "message": "Your Node is not  register in this NodeNetwork,broadcast failed"
        }
        print(
            f"BroadcastManager: {broadcast_src_node_id} is not registered in NodeManager")
        return jsonify(api_return), 403

    # NOTE : we should not broadcast to who send this broadcast
    may_active_nodes.remove(broadcast_src_node_id)
    print(broadcast_src_node_id, may_active_nodes)
    if may_active_nodes == []:
        # get node information failed
        api_return = {
            "message": "No online peer Node ,broadcast failed"
        }
        print(f"BroadcastManager: No online peer Node,broadcast failed")
        return jsonify(api_return), 200

    checked_alive_node = node_alive_check(may_active_nodes)
    if checked_alive_node == []:
        # after checking , node is online
        api_return = {
            "message": "After node alive check  no node is online ,broadcast failed"
        }
        print(
            f"BroadcastManager: After node alive check no node is online,broadcast failed")
        return jsonify(api_return), 500
    print("\n--------------BroadCasting------------------")
    broadcast_result = {
        "successful_node": [],
        "failed_node": [],
    }
    # get the rsa pub key for the broadcast_src_node_id
    pub_key = get_activate_node_rsa_public_key(broadcast_src_node_id)
    if pub_key == None:
        print(f"Get rsa public key failed for {broadcast_src_node_id}")
        # after checking , node is online
        api_return = {
            "message": "Get src_node_id RSA public key failed, broadcast fails"
        }
        return jsonify(api_return), 500

    for alive_node in checked_alive_node:
        # NOTE : node broadcast is only POST Method
        try:
            broadcast_with_rsa = {
                "src_node_public_key": pub_key,
                "payload": broadcast_payload
            }
            requests.post(
                f"http://{alive_node}{broadcast_endpoint}", json=broadcast_with_rsa, timeout=2)
            broadcast_result["successful_node"].append(alive_node)
            print("LOG: {} broadcast successfully".format(alive_node))
            continue
        except:
            broadcast_result["failed_node"].append(alive_node)
            print("ALERT: {} broadcast failed".format(alive_node))
            continue

    print("--------------BroadCasting------------------\n")
    api_return = {
        "message": "broadcast successfully",
        "broadcast_result": broadcast_result
    }
    print("---------------Success-----------------")
    return jsonify(api_return), 200


def register_service(node_manager_url):
    MAX_RETRIES = 5
    for retry in range(MAX_RETRIES):
        try:
            # register the node
            response = requests.get(
                f'{node_manager_url}/alive')
            if response.status_code == 200:
                # registration successful, return True
                return True
            else:
                print("Exceptional Alive Return Error")
                time.sleep(1)

        except:
            # catch exceptions raised by requests library
            print(
                f"BroadcastManager : NodeManager {NODE_MANAGER} => Request failed {retry+1}/{MAX_RETRIES}")
            # retry the request after a short delay
            time.sleep(1)
    else:
        # if we exit the loop without a break, registration failed
        print("NodeManager is DEAD !!")
        return False


# NODE_MANAGER address
# try to refer to the node manager
NODE_MANAGER = "http://nodemanager.default.svc.cluster.local:8000"


if __name__ == '__main__':

    if not register_service(NODE_MANAGER):
        print("Now shutdown BroadcastManager Since NodeManager is Dead ...")
        exit(1)

    print("NodeManager alive check successfully , now starting the BroadcastManager...")
    app.run(host="0.0.0.0", port=7000)
