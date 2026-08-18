import os
import json
import re
import shlex
import tempfile
import uuid

import paramiko
import pandas as pd
import streamlit as st

from kubernetes import client, config


# ============================================================
# PAGE CONFIG / CSS
# ============================================================

def render_css():

    st.markdown(
        """
        <style>

        .docker-title {
            font-size: 36px;
            font-weight: 700;
            color: #18213d;
            margin-bottom: 5px;
        }

        .docker-subtitle {
            font-size: 16px;
            color: #667085;
            margin-bottom: 25px;
        }

        .step-title {
            font-size: 22px;
            font-weight: 700;
            color: #18345e;
            margin-top: 20px;
            margin-bottom: 10px;
        }

        .source-card {
            padding: 18px;
            border-radius: 12px;
            border: 1px solid #dbe5f3;
            background: #f8fbff;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# SESSION STATE
# ============================================================

def initialize_state():

    defaults = {
        "docker_failures": [],
        "docker_scan_namespace": None,
        "docker_selected_image": None,
        "docker_image_pods": [],
        "docker_node_scan": [],
        "docker_source": None,
        "docker_source_image": None,
        "docker_source_node": None,
        "docker_source_ip": None,
        "docker_destination_checked": False,
        "docker_destination_has_image": False,
        "docker_transfer_done": False,
    }

    for key, value in defaults.items():

        if key not in st.session_state:
            st.session_state[key] = value


# ============================================================
# KUBECONFIG
# ============================================================

def load_kubeconfig(uploaded_file):

    kubeconfig_path = os.path.join(
        tempfile.gettempdir(),
        f"si_platform_kubeconfig_{uuid.uuid4().hex}.yaml",
    )

    with open(
        kubeconfig_path,
        "wb",
    ) as file:

        file.write(
            uploaded_file.getvalue()
        )

    try:

        config.load_kube_config(
            config_file=kubeconfig_path
        )

        return client.ApiClient()

    finally:

        try:
            os.remove(
                kubeconfig_path
            )
        except Exception:
            pass


# ============================================================
# KUBERNETES NAMESPACES
# ============================================================

def get_namespaces(
    api_client,
):

    core_api = client.CoreV1Api(
        api_client
    )

    namespace_list = (
        core_api.list_namespace()
    )

    return sorted(
        [
            item.metadata.name
            for item in namespace_list.items
        ]
    )


# ============================================================
# STEP 1
# FIND IMAGE PULL ERRORS
# ============================================================

def find_image_pull_errors(
    api_client,
    namespace,
):

    core_api = client.CoreV1Api(
        api_client
    )

    pods = (
        core_api.list_namespaced_pod(
            namespace=namespace
        )
    )

    results = []

    for pod in pods.items:

        statuses = (
            pod.status.container_statuses
            or []
        )

        for status in statuses:

            if not status.state:
                continue

            waiting = (
                status.state.waiting
            )

            if not waiting:
                continue

            reason = (
                waiting.reason
                or ""
            )

            if reason not in (
                "ImagePullBackOff",
                "ErrImagePull",
            ):
                continue

            image = ""

            for container in (
                pod.spec.containers
                or []
            ):

                if (
                    container.name
                    == status.name
                ):

                    image = (
                        container.image
                        or ""
                    )

                    break

            results.append(
                {
                    "Namespace": namespace,
                    "Pod": pod.metadata.name,
                    "Container": status.name,
                    "Image": image,
                    "Status": reason,
                    "Node": (
                        pod.spec.node_name
                        or ""
                    ),
                    "Message": (
                        waiting.message
                        or ""
                    ),
                }
            )

    return results


# ============================================================
# GET ALL RKE1 KUBERNETES NODES
# ============================================================

def get_cluster_nodes(
    api_client,
):

    core_api = client.CoreV1Api(
        api_client
    )

    node_list = (
        core_api.list_node()
    )

    nodes = []

    for node in node_list.items:

        node_name = (
            node.metadata.name
        )

        node_ip = None

        for address in (
            node.status.addresses
            or []
        ):

            if address.type == "InternalIP":

                node_ip = address.address

                break

        if node_ip:

            nodes.append(
                {
                    "name": node_name,
                    "ip": node_ip,
                }
            )

    return nodes


# ============================================================
# GET NODE IP
# ============================================================

def get_node_ip(
    api_client,
    node_name,
):

    core_api = client.CoreV1Api(
        api_client
    )

    node = (
        core_api.read_node(
            node_name
        )
    )

    for address in (
        node.status.addresses
        or []
    ):

        if address.type == "InternalIP":

            return address.address

    return None


# ============================================================
# STEP 2
# FIND ALL PODS USING SELECTED IMAGE
#
# Equivalent to:
#
# kubectl get pods -A -o json | jq -r '
# .items[]
# | select(.spec.containers[].image == "IMAGE")
# | [.metadata.namespace, .metadata.name, .spec.nodeName]
# | @tsv'
# ============================================================

def find_image_pods(
    api_client,
    image,
):

    core_api = client.CoreV1Api(
        api_client
    )

    pods = (
        core_api.list_pod_for_all_namespaces()
    )

    results = []

    for pod in pods.items:

        node_name = (
            pod.spec.node_name
        )

        if not node_name:
            continue

        for container in (
            pod.spec.containers
            or []
        ):

            if container.image == image:

                results.append(
                    {
                        "Namespace": (
                            pod.metadata.namespace
                        ),
                        "Pod": (
                            pod.metadata.name
                        ),
                        "Node": node_name,
                        "Image": image,
                    }
                )

    return results


# ============================================================
# SSH CONNECTION
# ============================================================

def create_ssh_connection(
    host,
    username,
    password=None,
    private_key=None,
):

    ssh = paramiko.SSHClient()

    ssh.set_missing_host_key_policy(
        paramiko.AutoAddPolicy()
    )

    if private_key:

        key = None

        loaders = [
            paramiko.RSAKey.from_private_key_file,
            paramiko.Ed25519Key.from_private_key_file,
            paramiko.ECDSAKey.from_private_key_file,
            paramiko.DSSKey.from_private_key_file,
        ]

        for loader in loaders:

            try:

                key = loader(
                    private_key
                )

                break

            except Exception:
                continue

        if key is None:

            raise Exception(
                "Unable to read SSH private key."
            )

        ssh.connect(
            hostname=host,
            username=username,
            pkey=key,
            timeout=20,
            banner_timeout=20,
            auth_timeout=20,
        )

    else:

        ssh.connect(
            hostname=host,
            username=username,
            password=password,
            timeout=20,
            banner_timeout=20,
            auth_timeout=20,
        )

    return ssh


# ============================================================
# SSH COMMAND
# ============================================================

def run_ssh_command(
    ssh,
    command,
    timeout=300,
):

    stdin, stdout, stderr = (
        ssh.exec_command(
            command,
            timeout=timeout,
        )
    )

    exit_code = (
        stdout.channel.recv_exit_status()
    )

    output = (
        stdout.read()
        .decode(
            errors="replace"
        )
    )

    error = (
        stderr.read()
        .decode(
            errors="replace"
        )
    )

    return (
        exit_code,
        output,
        error,
    )


# ============================================================
# DZDO ROOT COMMAND
#
# User requirement:
#
# ssh user@vm
# dzdo -i
# docker ...
#
# We automate that as:
#
# dzdo -i bash -lc 'docker ...'
# ============================================================

def dzdo_command(
    docker_command,
):

    return (
        "dzdo -i bash -lc "
        + shlex.quote(
            docker_command
        )
    )


# ============================================================
# CHECK DOCKER
# ============================================================

def check_docker(
    ssh,
):

    command = dzdo_command(
        "docker --version"
    )

    exit_code, output, error = (
        run_ssh_command(
            ssh,
            command,
        )
    )

    return exit_code == 0


# ============================================================
# GET DOCKER IMAGES
# ============================================================

def get_docker_images(
    ssh,
):

    command = dzdo_command(
        "docker images --format "
        "'{{.Repository}}:{{.Tag}}'"
    )

    exit_code, output, error = (
        run_ssh_command(
            ssh,
            command,
        )
    )

    if exit_code != 0:

        return []

    return [
        line.strip()
        for line in output.splitlines()
        if line.strip()
    ]


# ============================================================
# CHECK SPECIFIC IMAGE
# ============================================================

def check_image_on_vm(
    ssh,
    image,
):

    command = dzdo_command(
        "docker images --format "
        "'{{.Repository}}:{{.Tag}}' "
        "| grep -Fx "
        + shlex.quote(
            image
        )
    )

    exit_code, output, error = (
        run_ssh_command(
            ssh,
            command,
        )
    )

    return (
        exit_code == 0
        and image in output.splitlines()
    )


# ============================================================
# IMAGE DETAILS
# ============================================================

def get_image_details(
    ssh,
    image,
):

    command = dzdo_command(
        "docker images --format "
        "'{{.Repository}}:{{.Tag}}|{{.ID}}|{{.Size}}'"
    )

    exit_code, output, error = (
        run_ssh_command(
            ssh,
            command,
        )
    )

    if exit_code != 0:

        return None

    for line in output.splitlines():

        parts = line.strip().split(
            "|"
        )

        if len(parts) != 3:
            continue

        if parts[0] == image:

            return {
                "image": parts[0],
                "id": parts[1],
                "size": parts[2],
            }

    return None


# ============================================================
# SEARCH IMAGE ON VM
# ============================================================

def search_image_on_vm(
    node_name,
    node_ip,
    username,
    password,
    private_key,
    image,
):

    result = {
        "Node": node_name,
        "IP": node_ip,
        "Docker": "Unknown",
        "Image": "Not Found",
        "Details": "",
    }

    ssh = None

    try:

        ssh = create_ssh_connection(
            host=node_ip,
            username=username,
            password=password,
            private_key=private_key,
        )

        if not check_docker(
            ssh
        ):

            result["Docker"] = (
                "Unavailable"
            )

            result["Details"] = (
                "Unable to execute Docker "
                "through dzdo -i."
            )

            return (
                False,
                result,
            )

        result["Docker"] = "Available"

        details = get_image_details(
            ssh,
            image,
        )

        if details:

            result["Image"] = "FOUND"

            result["Details"] = (
                f"ID: {details['id']} | "
                f"Size: {details['size']}"
            )

            return (
                True,
                {
                    **result,
                    "details": details,
                },
            )

        result["Image"] = "Not Found"

        result["Details"] = (
            "Image not present in docker images."
        )

        return (
            False,
            result,
        )

    except Exception as exc:

        result["Details"] = str(
            exc
        )

        return (
            False,
            result,
        )

    finally:

        if ssh:

            try:
                ssh.close()
            except Exception:
                pass


# ============================================================
# SEARCH IMAGE
#
# Priority:
#
# 1. Nodes where Kubernetes currently uses image
# 2. ALL RKE1 nodes
# ============================================================

def search_image_across_cluster(
    api_client,
    image,
    image_pods,
    cluster_nodes,
    username,
    password,
    private_key,
):

    ordered_nodes = []

    seen = set()

    # --------------------------------------------------------
    # FIRST: NODES WHERE IMAGE IS CURRENTLY REFERENCED
    # --------------------------------------------------------

    for pod in image_pods:

        node_name = pod["Node"]

        node_ip = None

        for node in cluster_nodes:

            if node["name"] == node_name:

                node_ip = node["ip"]

                break

        if (
            node_ip
            and node_ip not in seen
        ):

            ordered_nodes.append(
                {
                    "name": node_name,
                    "ip": node_ip,
                }
            )

            seen.add(
                node_ip
            )

    # --------------------------------------------------------
    # SECOND: ALL OTHER RKE1 NODES
    # --------------------------------------------------------

    for node in cluster_nodes:

        if node["ip"] in seen:
            continue

        ordered_nodes.append(
            node
        )

        seen.add(
            node["ip"]
        )

    scan_results = []

    source = None

    progress = st.progress(
        0
    )

    status = st.empty()

    total = len(
        ordered_nodes
    )

    for index, node in enumerate(
        ordered_nodes
    ):

        node_name = node["name"]
        node_ip = node["ip"]

        status.info(
            f"🔎 Checking "
            f"{node_name} "
            f"({node_ip})"
        )

        found, result = (
            search_image_on_vm(
                node_name=node_name,
                node_ip=node_ip,
                username=username,
                password=password,
                private_key=private_key,
                image=image,
            )
        )

        scan_results.append(
            result
        )

        progress.progress(
            (index + 1) / total
            if total
            else 1
        )

        if found:

            source = {
                "node": node_name,
                "ip": node_ip,
                "details": result.get(
                    "details"
                ),
            }

            break

    status.empty()

    return (
        source,
        scan_results,
    )


# ============================================================
# SAVE DOCKER IMAGE
# ============================================================

def docker_save(
    ssh,
    image,
    tar_path,
):

    command = dzdo_command(
        "docker save "
        "-o "
        + shlex.quote(
            tar_path
        )
        + " "
        + shlex.quote(
            image
        )
    )

    return run_ssh_command(
        ssh,
        command,
        timeout=1800,
    )


# ============================================================
# GET REMOTE FILE SIZE
# ============================================================

def get_remote_file_size(
    ssh,
    path,
):

    command = (
        "stat -c '%s' "
        + shlex.quote(
            path
        )
    )

    exit_code, output, error = (
        run_ssh_command(
            ssh,
            command,
        )
    )

    if exit_code != 0:

        return None

    try:

        return int(
            output.strip()
        )

    except Exception:

        return None


# ============================================================
# TRANSFER TAR
#
# Source VM → local SI-PLATFORM VM → destination VM
#
# This avoids requiring source VM to SSH into destination VM.
# ============================================================

def transfer_tar(
    source_ssh,
    source_tar,
    destination_ssh,
    destination_tar,
):

    local_tar = os.path.join(
        tempfile.gettempdir(),
        f"si_image_{uuid.uuid4().hex}.tar",
    )

    try:

        # ----------------------------------------------------
        # SOURCE → LOCAL
        # ----------------------------------------------------

        source_sftp = (
            source_ssh.open_sftp()
        )

        try:

            source_sftp.get(
                source_tar,
                local_tar,
            )

        finally:

            source_sftp.close()

        # ----------------------------------------------------
        # LOCAL → DESTINATION
        # ----------------------------------------------------

        destination_sftp = (
            destination_ssh.open_sftp()
        )

        try:

            destination_sftp.put(
                local_tar,
                destination_tar,
            )

        finally:

            destination_sftp.close()

    finally:

        try:

            if os.path.exists(
                local_tar
            ):

                os.remove(
                    local_tar
                )

        except Exception:
            pass


# ============================================================
# MOVE TAR TO ROOT
# ============================================================

def move_tar_to_root(
    ssh,
    user_tar,
):

    filename = os.path.basename(
        user_tar
    )

    root_tar = (
        "/root/"
        + filename
    )

    command = dzdo_command(
        "mv "
        + shlex.quote(
            user_tar
        )
        + " "
        + shlex.quote(
            root_tar
        )
    )

    exit_code, output, error = (
        run_ssh_command(
            ssh,
            command,
        )
    )

    if exit_code != 0:

        raise Exception(
            "Failed to move TAR to /root:\n"
            + (
                error
                or output
            )
        )

    return root_tar


# ============================================================
# DOCKER LOAD
# ============================================================

def docker_load(
    ssh,
    root_tar,
):

    command = dzdo_command(
        "docker load -i "
        + shlex.quote(
            root_tar
        )
    )

    return run_ssh_command(
        ssh,
        command,
        timeout=1800,
    )


# ============================================================
# REMOVE FILE
# ============================================================

def remove_file(
    ssh,
    path,
    privileged=False,
):

    if privileged:

        command = dzdo_command(
            "rm -f "
            + shlex.quote(
                path
            )
        )

    else:

        command = (
            "rm -f "
            + shlex.quote(
                path
            )
        )

    return run_ssh_command(
        ssh,
        command,
    )


# ============================================================
# MAIN UI
# ============================================================

def render_docker_image_load():

    initialize_state()

    render_css()

    # ========================================================
    # HEADER
    # ========================================================

    st.markdown(
        '<div class="docker-title">'
        '🐳 Docker Image Load'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="docker-subtitle">'
        'RKE1 ImagePullBackOff image detection, '
        'source VM discovery and Docker image transfer.'
        '</div>',
        unsafe_allow_html=True,
    )

    # ========================================================
    # STEP 1
    # ========================================================

    st.markdown(
        '<div class="step-title">'
        '1️⃣ Upload Kubeconfig'
        '</div>',
        unsafe_allow_html=True,
    )

    kubeconfig_file = st.file_uploader(
        "Upload RKE1 kubeconfig",
        type=[
            "yaml",
            "yml",
            "conf",
        ],
        key="docker_kubeconfig",
    )

    if kubeconfig_file is None:

        st.info(
            "Upload the kubeconfig file to continue."
        )

        return

    # --------------------------------------------------------
    # CONNECT
    # --------------------------------------------------------

    try:

        api_client = load_kubeconfig(
            kubeconfig_file
        )

        namespaces = get_namespaces(
            api_client
        )

        cluster_nodes = get_cluster_nodes(
            api_client
        )

    except Exception as exc:

        st.error(
            "Failed to connect to Kubernetes cluster:\n\n"
            + str(exc)
        )

        return

    st.success(
        f"✅ Connected to Kubernetes. "
        f"{len(cluster_nodes)} nodes detected."
    )

    # ========================================================
    # NAMESPACE
    # ========================================================

    st.markdown(
        '<div class="step-title">'
        '2️⃣ Select Namespace'
        '</div>',
        unsafe_allow_html=True,
    )

    selected_namespace = st.selectbox(
        "Namespace",
        namespaces,
        key="docker_namespace",
    )

    # --------------------------------------------------------
    # EXACT USER COMMAND DISPLAY
    # --------------------------------------------------------

    st.code(
        "kubectl get pods -n "
        + selected_namespace
        + " | egrep "
        "'ImagePullBackOff|ErrImagePull'",
        language="bash",
    )

    # --------------------------------------------------------
    # SCAN
    # --------------------------------------------------------

    if st.button(
        "🔍 Search ImagePullBackOff / ErrImagePull",
        use_container_width=True,
        type="primary",
        key="docker_scan_button",
    ):

        try:

            failures = (
                find_image_pull_errors(
                    api_client,
                    selected_namespace,
                )
            )

            st.session_state[
                "docker_failures"
            ] = failures

            st.session_state[
                "docker_scan_namespace"
            ] = selected_namespace

            st.session_state[
                "docker_source"
            ] = None

        except Exception as exc:

            st.error(
                "Failed to scan pods:\n\n"
                + str(exc)
            )

            return

    # ========================================================
    # FAILED POD RESULTS
    # ========================================================

    failures = (
        st.session_state[
            "docker_failures"
        ]
    )

    if (
        st.session_state[
            "docker_scan_namespace"
        ]
        != selected_namespace
    ):

        failures = []

    if not failures:

        st.info(
            "No ImagePullBackOff or ErrImagePull "
            "pods found in the selected namespace."
        )

        return

    st.markdown(
        "### 🚨 Image Pull Failures"
    )

    failure_df = pd.DataFrame(
        failures
    )

    st.dataframe(
        failure_df,
        use_container_width=True,
        hide_index=True,
    )

    # ========================================================
    # SELECT IMAGE
    # ========================================================

    images = sorted(
        list(
            set(
                item["Image"]
                for item in failures
                if item.get("Image")
            )
        )
    )

    if not images:

        st.warning(
            "No image name could be extracted."
        )

        return

    selected_image = st.selectbox(
        "Select Image to Fix",
        images,
        key="docker_selected_image",
    )

    # ========================================================
    # STEP 2
    # ========================================================

    st.markdown(
        '<div class="step-title">'
        '3️⃣ Find VM Having the Image'
        '</div>',
        unsafe_allow_html=True,
    )

    st.code(
        "kubectl get pods -A -o json | jq -r '\n"
        ".items[]\n"
        "| select(.spec.containers[].image == "
        + json.dumps(
            selected_image
        )
        + ")\n"
        "| [.metadata.namespace, "
        ".metadata.name, .spec.nodeName]\n"
        "| @tsv'",
        language="bash",
    )

    # --------------------------------------------------------
    # FIND PODS USING IMAGE
    # --------------------------------------------------------

    if st.button(
        "🔎 Find Image Source VM",
        use_container_width=True,
        type="primary",
        key="docker_find_source_button",
    ):

        try:

            with st.spinner(
                "Finding pods using selected image..."
            ):

                image_pods = (
                    find_image_pods(
                        api_client,
                        selected_image,
                    )
                )

            st.session_state[
                "docker_image_pods"
            ] = image_pods

            if not image_pods:

                st.warning(
                    "No running pod currently references "
                    "this image."
                )

            else:

                st.success(
                    f"Found {len(image_pods)} pod(s) "
                    "using this image."
                )

        except Exception as exc:

            st.error(
                "Failed to search image usage:\n\n"
                + str(exc)
            )

    image_pods = (
        st.session_state[
            "docker_image_pods"
        ]
    )

    # --------------------------------------------------------
    # IMAGE PODS TABLE
    # --------------------------------------------------------

    if image_pods:

        st.markdown(
            "### Kubernetes Workloads Using Image"
        )

        st.dataframe(
            pd.DataFrame(
                image_pods
            ),
            use_container_width=True,
            hide_index=True,
        )

    # ========================================================
    # SSH CREDENTIALS
    # ========================================================

    st.markdown(
        "### 🔐 RKE1 VM SSH Access"
    )

    ssh_username = st.text_input(
        "SSH Username",
        value="ananth.rajathinam",
        key="docker_ssh_username",
    )

    auth_type = st.radio(
        "SSH Authentication",
        [
            "Password",
            "Private Key",
        ],
        horizontal=True,
        key="docker_auth_type",
    )

    ssh_password = None
    ssh_private_key = None

    if auth_type == "Password":

        ssh_password = st.text_input(
            "SSH Password",
            type="password",
            key="docker_ssh_password",
        )

    else:

        ssh_private_key = st.text_area(
            "SSH Private Key",
            height=180,
            placeholder=(
                "-----BEGIN OPENSSH PRIVATE KEY-----"
            ),
            key="docker_private_key",
        )

    # ========================================================
    # SEARCH ALL RKE1 VMS
    # ========================================================

    if st.button(
        "🔍 Search Image Across All RKE1 VMs",
        use_container_width=True,
        key="docker_search_all_vms",
    ):

        if not ssh_username:

            st.error(
                "Enter SSH username."
            )

            return

        if (
            auth_type == "Password"
            and not ssh_password
        ):

            st.error(
                "Enter SSH password."
            )

            return

        if (
            auth_type == "Private Key"
            and not ssh_private_key
        ):

            st.error(
                "Enter SSH private key."
            )

            return

        try:

            with st.spinner(
                "Searching Docker image across RKE1 VMs..."
            ):

                source, scan_results = (
                    search_image_across_cluster(
                        api_client=api_client,
                        image=selected_image,
                        image_pods=image_pods,
                        cluster_nodes=cluster_nodes,
                        username=ssh_username,
                        password=ssh_password,
                        private_key=ssh_private_key,
                    )
                )

            st.session_state[
                "docker_node_scan"
            ] = scan_results

            st.session_state[
                "docker_source"
            ] = source

        except Exception as exc:

            st.error(
                "Failed to search RKE1 VMs:\n\n"
                + str(exc)
            )

    # ========================================================
    # VM SEARCH RESULTS
    # ========================================================

    scan_results = (
        st.session_state[
            "docker_node_scan"
        ]
    )

    if scan_results:

        st.markdown(
            "### 🖥️ RKE1 VM Image Search"
        )

        scan_df = pd.DataFrame(
            scan_results
        )

        st.dataframe(
            scan_df,
            use_container_width=True,
            hide_index=True,
        )

    # ========================================================
    # SOURCE FOUND
    # ========================================================

    source = (
        st.session_state[
            "docker_source"
        ]
    )

    if not source:

        if scan_results:

            st.error(
                f"❌ Image `{selected_image}` "
                "was not found on any RKE1 VM."
            )

        return

    source_ip = source["ip"]
    source_node = source["node"]

    st.success(
        f"✅ Image found on source VM: "
        f"`{source_node}` / `{source_ip}`"
    )

    if source.get("details"):

        details = source["details"]

        c1, c2, c3 = st.columns(3)

        with c1:

            st.metric(
                "Source VM",
                source_ip,
            )

        with c2:

            st.metric(
                "Image ID",
                details.get(
                    "id",
                    "-",
                ),
            )

        with c3:

            st.metric(
                "Image Size",
                details.get(
                    "size",
                    "-",
                ),
            )

    # ========================================================
    # STEP 3
    # ========================================================

    st.markdown(
        '<div class="step-title">'
        '4️⃣ Source VM - Docker Save'
        '</div>',
        unsafe_allow_html=True,
    )

    st.code(
        "ssh "
        + ssh_username
        + "@"
        + source_ip
        + "\n"
        "dzdo -i\n"
        "docker images | grep "
        + shlex.quote(
            selected_image
        )
        + "\n"
        "docker save -o "
        + selected_image.split(
            "/"
        )[-1].replace(
            ":",
            "-",
        )
        + ".tar "
        + selected_image,
        language="bash",
    )

    # --------------------------------------------------------
    # SOURCE TAR
    # --------------------------------------------------------

    safe_image_name = re.sub(
        r"[^A-Za-z0-9_.-]",
        "_",
        selected_image,
    )

    source_tar = (
        "/tmp/"
        + safe_image_name
        + ".tar"
    )

    if st.button(
        "📦 Create Docker TAR on Source VM",
        use_container_width=True,
        key="docker_save_button",
    ):

        if not ssh_username:

            st.error(
                "Enter SSH username."
            )

            return

        if (
            auth_type == "Password"
            and not ssh_password
        ):

            st.error(
                "Enter SSH password."
            )

            return

        try:

            with st.spinner(
                "Connecting to source VM..."
            ):

                source_ssh = (
                    create_ssh_connection(
                        host=source_ip,
                        username=ssh_username,
                        password=ssh_password,
                        private_key=ssh_private_key,
                    )
                )

            try:

                if not check_docker(
                    source_ssh
                ):

                    raise Exception(
                        "Docker is not accessible "
                        "through dzdo -i on source VM."
                    )

                if not check_image_on_vm(
                    source_ssh,
                    selected_image,
                ):

                    raise Exception(
                        "Image is no longer available "
                        "on source VM."
                    )

                with st.spinner(
                    "Running docker save..."
                ):

                    exit_code, output, error = (
                        docker_save(
                            source_ssh,
                            selected_image,
                            source_tar,
                        )
                    )

                if exit_code != 0:

                    raise Exception(
                        "docker save failed:\n"
                        + (
                            error
                            or output
                        )
                    )

                tar_size = (
                    get_remote_file_size(
                        source_ssh,
                        source_tar,
                    )
                )

                st.session_state[
                    "docker_source_tar"
                ] = source_tar

                st.session_state[
                    "docker_source_tar_size"
                ] = tar_size

                st.success(
                    f"✅ Docker TAR created: "
                    f"`{source_tar}`"
                )

                if tar_size:

                    st.info(
                        "TAR size: "
                        f"{tar_size / 1024 / 1024:.2f} MB"
                    )

            finally:

                source_ssh.close()

        except Exception as exc:

            st.error(
                "Failed to create Docker TAR:\n\n"
                + str(exc)
            )

    # ========================================================
    # CHECK TAR CREATED
    # ========================================================

    saved_tar = (
        st.session_state.get(
            "docker_source_tar"
        )
    )

    if not saved_tar:

        return

    # ========================================================
    # STEP 4
    # DESTINATION
    # ========================================================

    st.markdown(
        '<div class="step-title">'
        '5️⃣ Destination VM'
        '</div>',
        unsafe_allow_html=True,
    )

    st.info(
        "Enter the destination VM where the image "
        "needs to be loaded."
    )

    destination_ip = st.text_input(
        "Destination VM IP",
        placeholder="172.30.201.57",
        key="docker_destination_ip",
    )

    destination_username = st.text_input(
        "Destination SSH Username",
        value=ssh_username,
        key="docker_destination_username",
    )

    destination_auth_type = st.radio(
        "Destination SSH Authentication",
        [
            "Same Credentials",
            "Different Password",
            "Different Private Key",
        ],
        horizontal=True,
        key="docker_destination_auth",
    )

    destination_password = None
    destination_private_key = None

    if (
        destination_auth_type
        == "Same Credentials"
    ):

        destination_password = (
            ssh_password
        )

        destination_private_key = (
            ssh_private_key
        )

    elif (
        destination_auth_type
        == "Different Password"
    ):

        destination_password = st.text_input(
            "Destination SSH Password",
            type="password",
            key="docker_destination_password",
        )

    else:

        destination_private_key = st.text_area(
            "Destination Private Key",
            height=180,
            key="docker_destination_private_key",
        )

    destination_directory = st.text_input(
        "Destination TAR Directory",
        value=(
            "/home/"
            + destination_username
        ),
        key="docker_destination_directory",
    )

    # ========================================================
    # CHECK DESTINATION
    # ========================================================

    if st.button(
        "🔎 Check Destination Image",
        use_container_width=True,
        key="docker_check_destination",
    ):

        if not destination_ip:

            st.error(
                "Enter destination VM IP."
            )

            return

        if not destination_username:

            st.error(
                "Enter destination SSH username."
            )

            return

        if (
            destination_auth_type
            == "Same Credentials"
        ):

            if (
                not destination_password
                and not destination_private_key
            ):

                st.error(
                    "Source SSH credentials are not available."
                )

                return

        if (
            destination_auth_type
            == "Different Password"
            and not destination_password
        ):

            st.error(
                "Enter destination password."
            )

            return

        if (
            destination_auth_type
            == "Different Private Key"
            and not destination_private_key
        ):

            st.error(
                "Enter destination private key."
            )

            return

        destination_ssh = None

        try:

            with st.spinner(
                "Connecting to destination VM..."
            ):

                destination_ssh = (
                    create_ssh_connection(
                        host=destination_ip,
                        username=destination_username,
                        password=destination_password,
                        private_key=destination_private_key,
                    )
                )

            if not check_docker(
                destination_ssh
            ):

                raise Exception(
                    "Docker is not accessible "
                    "through dzdo -i on destination VM."
                )

            image_exists = (
                check_image_on_vm(
                    destination_ssh,
                    selected_image,
                )
            )

            st.session_state[
                "docker_destination_checked"
            ] = True

            st.session_state[
                "docker_destination_has_image"
            ] = image_exists

            if image_exists:

                st.success(
                    "✅ Image already exists on "
                    "destination VM."
                )

            else:

                st.warning(
                    "❌ Image is not present on "
                    "destination VM."
                )

        except Exception as exc:

            st.error(
                "Destination connection failed:\n\n"
                + str(exc)
            )

        finally:

            if destination_ssh:

                try:
                    destination_ssh.close()
                except Exception:
                    pass

    # ========================================================
    # DESTINATION ALREADY HAS IMAGE
    # ========================================================

    if (
        st.session_state[
            "docker_destination_checked"
        ]
        and st.session_state[
            "docker_destination_has_image"
        ]
    ):

        st.success(
            "🎯 Nothing to transfer. "
            "Destination already contains the image."
        )

        return

    # ========================================================
    # TRANSFER BUTTON
    # ========================================================

    if not st.session_state[
        "docker_destination_checked"
    ]:

        return

    st.markdown(
        '<div class="step-title">'
        '6️⃣ Transfer → Load → Verify → Cleanup'
        '</div>',
        unsafe_allow_html=True,
    )

    if st.button(
        "🚀 Transfer & Load Image",
        use_container_width=True,
        type="primary",
        key="docker_transfer_button",
    ):

        source_ssh = None
        destination_ssh = None

        destination_tar = None
        root_tar = None

        try:

            # =================================================
            # SOURCE LOGIN
            # =================================================

            st.write(
                "🔌 Connecting to source VM..."
            )

            source_ssh = (
                create_ssh_connection(
                    host=source_ip,
                    username=ssh_username,
                    password=ssh_password,
                    private_key=ssh_private_key,
                )
            )

            st.success(
                f"✅ Source VM connected: "
                f"{source_ip}"
            )

            # =================================================
            # VERIFY SOURCE IMAGE
            # =================================================

            if not check_image_on_vm(
                source_ssh,
                selected_image,
            ):

                raise Exception(
                    "Image is no longer present "
                    "on source VM."
                )

            # =================================================
            # DESTINATION LOGIN
            # =================================================

            st.write(
                "🔌 Connecting to destination VM..."
            )

            destination_ssh = (
                create_ssh_connection(
                    host=destination_ip,
                    username=destination_username,
                    password=destination_password,
                    private_key=destination_private_key,
                )
            )

            st.success(
                f"✅ Destination VM connected: "
                f"{destination_ip}"
            )

            # =================================================
            # DESTINATION DOCKER
            # =================================================

            if not check_docker(
                destination_ssh
            ):

                raise Exception(
                    "Docker is not accessible "
                    "through dzdo -i on destination."
                )

            # =================================================
            # DESTINATION IMAGE CHECK AGAIN
            # =================================================

            if check_image_on_vm(
                destination_ssh,
                selected_image,
            ):

                st.success(
                    "✅ Image already exists on "
                    "destination."
                )

                return

            # =================================================
            # DESTINATION DIRECTORY
            # =================================================

            safe_name = os.path.basename(
                saved_tar
            )

            destination_tar = (
                destination_directory.rstrip(
                    "/"
                )
                + "/"
                + safe_name
            )

            st.write(
                "📁 Creating destination directory..."
            )

            exit_code, output, error = (
                run_ssh_command(
                    destination_ssh,
                    "mkdir -p "
                    + shlex.quote(
                        destination_directory
                    ),
                )
            )

            if exit_code != 0:

                raise Exception(
                    "Unable to create destination "
                    "directory:\n"
                    + (
                        error
                        or output
                    )
                )

            # =================================================
            # TRANSFER
            # =================================================

            st.write(
                "📤 Transferring TAR from source "
                "VM to destination VM..."
            )

            transfer_tar(
                source_ssh,
                saved_tar,
                destination_ssh,
                destination_tar,
            )

            st.success(
                "✅ TAR transferred successfully."
            )

            # =================================================
            # MOVE TO ROOT
            # =================================================

            st.write(
                "🔐 Moving TAR to /root using dzdo -i..."
            )

            root_tar = (
                "/root/"
                + safe_name
            )

            move_command = dzdo_command(
                "mv "
                + shlex.quote(
                    destination_tar
                )
                + " "
                + shlex.quote(
                    root_tar
                )
            )

            exit_code, output, error = (
                run_ssh_command(
                    destination_ssh,
                    move_command,
                )
            )

            if exit_code != 0:

                raise Exception(
                    "Failed to move TAR to /root:\n"
                    + (
                        error
                        or output
                    )
                )

            st.success(
                f"✅ TAR moved to `{root_tar}`"
            )

            # =================================================
            # DOCKER LOAD
            # =================================================

            st.write(
                "🐳 Loading image using Docker..."
            )

            exit_code, output, error = (
                docker_load(
                    destination_ssh,
                    root_tar,
                )
            )

            if exit_code != 0:

                raise Exception(
                    "docker load failed:\n"
                    + (
                        error
                        or output
                    )
                )

            st.success(
                "✅ docker load completed."
            )

            if output.strip():

                st.code(
                    output,
                    language="text",
                )

            # =================================================
            # VERIFY
            # =================================================

            st.write(
                "🔎 Verifying image on destination..."
            )

            verified = check_image_on_vm(
                destination_ssh,
                selected_image,
            )

            if not verified:

                raise Exception(
                    "Image load completed but "
                    "verification failed."
                )

            st.success(
                "✅ Image successfully verified "
                "on destination VM."
            )

            # =================================================
            # CLEANUP SOURCE TAR
            # =================================================

            st.write(
                "🧹 Removing source TAR..."
            )

            remove_file(
                source_ssh,
                saved_tar,
                privileged=True,
            )

            st.success(
                "✅ Source TAR removed."
            )

            # =================================================
            # CLEANUP DESTINATION ROOT TAR
            # =================================================

            st.write(
                "🧹 Removing destination TAR..."
            )

            remove_file(
                destination_ssh,
                root_tar,
                privileged=True,
            )

            # =================================================
            # CLEANUP USER TAR
            # =================================================

            remove_file(
                destination_ssh,
                destination_tar,
                privileged=False,
            )

            st.success(
                "✅ Destination TAR removed."
            )

            # =================================================
            # COMPLETE
            # =================================================

            st.session_state[
                "docker_transfer_done"
            ] = True

            st.success(
                "🎉 Complete! Docker image "
                "successfully transferred and loaded."
            )

            st.code(
                "Image      : "
                + selected_image
                + "\n"
                "Source VM  : "
                + source_ip
                + "\n"
                "Source Node: "
                + source_node
                + "\n"
                "Destination: "
                + destination_ip,
                language="text",
            )

        except Exception as exc:

            st.error(
                "❌ Image transfer failed:\n\n"
                + str(exc)
            )

        finally:

            if source_ssh:

                try:
                    source_ssh.close()
                except Exception:
                    pass

            if destination_ssh:

                try:
                    destination_ssh.close()
                except Exception:
                    pass