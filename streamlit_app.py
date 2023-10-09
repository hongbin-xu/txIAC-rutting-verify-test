import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(layout="wide", 
                   page_title='IAC-Rutting Verification',
                   menu_items={
                       'Get help': "mailto:hongbinxu@utexas.edu",
                       'About': "Developed and maintained by Hongbin Xu"})

# Authentication function
def check_password():
    """Returns `True` if the user had a correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if (
            st.session_state["username"] in st.secrets["passwords"]
            and st.session_state["password"]
            == st.secrets["passwords"][st.session_state["username"]]
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store username + password
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show inputs for username + password.
        st.text_input("Username", on_change=password_entered, key="username")
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input("Username", on_change=password_entered, key="username")
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 User not known or password incorrect")
        return False
    else:
        # Password correct.
        return True

@st.cache_data
def dataLoad(_conn, segID=None, idmin = None, idmax=None):
    """
    mode1: select for each segment
    mode2: select for multiple segment
    creating 2d array of the height measurement
    """
    data = conn.query('SELECT * from pathway_raw_fm365_sep13 WHERE id BETWEEN '+ str(idmin) +' AND ' + str(idmax)+';')
    dataArray = np.array([np.array(data["height"][i].split(b',')).astype("float") for i in range(data.shape[0])])
    data = data.drop(columns = "height")
    data[[str(i) for i in range(1536)]] = dataArray
    height_max = data
    del dataArray
    return data, height_max

@st.cache_data
def transExtrac(segData, id, max_val):
    # Extract transverse profile
    scanData = segData.loc[(segData["id"]==id), ["tranStep"]+ [str(i) for i in range(1536)]].reset_index(drop=True)
    scanData_v1 = pd.DataFrame({"DIST":scanData["tranStep"][0]*np.arange(1536), "Height":scanData[[str(i) for i in range(1536)]].values.flatten()})

    # Plot transverse profile
    fig = px.line(scanData_v1, x="DIST", y="Height", labels = {"DIST": "Transverse OFFSET (mm)", "Height": "Height (mm}"}, template = "plotly_dark")
    #fig.update_layout(yaxis_range=[0,max_val])
    fig.layout.yaxis.range = [0,max_val]
    st.plotly_chart(fig, use_container_width=True, theme = None)
    return scanData_v1

@st.cache_data
def lonExtrac(segData, id, max_val):
    scanData = segData[["id", "OFFSET", str(id)]].rename(columns = {str(id): "Height"})
                # Plot transverse profile
    fig = px.line(scanData, x ="id", y="Height", labels = {"id": "Longitudinal id","Height": "Height (mm}"}, template = "plotly_dark")
    #fig.update_layout(yaxis_range=[0,max_val])
    fig.layout.yaxis.range = [0,max_val]
    st.plotly_chart(fig, use_container_width=True, theme = None)
    return scanData

@st.cache_data
def surfPlot(data):
    dataArray = data[[str(i) for i in range(1536)]]
    # hover information
    # id, segID, scanID, dataNum, DFO + mm, transverse mm
    customData= np.stack([data["segID"].values.reshape(dataArray.shape[0],-1).repeat(dataArray.shape[1], axis =1), # SegID 0
                         data["DFO"].values.reshape(dataArray.shape[0],-1).repeat(dataArray.shape[1], axis =1), # DFO 1
                         data["OFFSET"].values.reshape(dataArray.shape[0],-1).repeat(dataArray.shape[1], axis =1), # DFO offset 2
                         np.arange(dataArray.shape[1]).reshape(-1,dataArray.shape[1]).repeat(dataArray.shape[0], axis=0)*data["tranStep"].values.reshape(-1,1)], axis = -1)
    
    fig = px.imshow(dataArray, origin = "lower", 
                    labels = {"x": "Transverse id", "y": "Longitudinal id", "color": "Height (mm)"},
                    y = data["id"], #np.arange(dataArray.shape[0])*lonStep,
                    aspect="auto", 
                    height = 900)

    fig.update(data=[{'customdata': customData,
                      'hovertemplate': "<br>".join(["id: %{y:.0f}", "segID: %{customdata[0]:.0f}", "DFO: %{customdata[1]:.3f} mile",
                                                    "lonOFFSET: %{customdata[2]:.0f} mm", "transID: %{x:.0f}",
                                                    "transOFFSET: %{customdata[3]:.0f} mm","Height: %{z} mm"])}])

    fig['layout']['xaxis']['autorange'] = "reversed"
    st.plotly_chart(fig, use_container_width=True, theme = None)

# Check authentication
if check_password():    
    # Page title
    conn = st.experimental_connection("mysql", type="sql")
    
    # MySQL connection
    col1, col2 = st.columns(2, gap = "medium")
    with col1:
        with st.container():
            st.subheader("Suface")
            col11, col12 = st.columns(2)
            with col11:
                idmin = st.number_input("id start", min_value=1, max_value=90000-1, value = 1, step= 1)
            with col12:
                idmax = st.number_input("id end", min_value=idmin, max_value=min(90000, idmin + 4499), value = idmin+50, step= 1)

            # Load data
            if st.button("Update"):
                st.session_state.data, st.session_state.height_max = dataLoad(_conn=conn, idmin= idmin, idmax=idmax)
            
            if 'data' in st.session_state:
                st.write(str(st.session_state.data["ROUTE_NAME"][0])+ ", DFO: "+str(st.session_state.data["DFO"].min())+ "~"+ str(st.session_state.data["DFO"].max()))
                # plot surface
                surfPlot(data=st.session_state.data)

    if 'data' in st.session_state:
        with col2:
            with st.container():
                st.subheader("Transverse Profile")
                id_ = st.number_input("Transverse profile", min_value=idmin, max_value=idmax, step = 1)
                segID = id_//900+1
                #if st.button("Update transverse profile"):
                # Extract transverse profile
                scanData_v1 = transExtrac(segData = st.session_state.data, id=id_, max_val = st.session_state.height_max)

                # View and download data
                st.download_button(label="Download transverse profile", data=scanData_v1.to_csv().encode('utf-8'), file_name="transProfile_seg_" +str(segID)+"_scan_"+str(id_)+".csv", mime = "csv")

            with st.container():
                st.subheader("Longitudinal Profile")
                id_x = st.number_input("Longitudinal profile", min_value=0, max_value=1536,value=0, step = 1)

                # Extract transverse profile
                scanData_v2 = lonExtrac(segData = st.session_state.data, id=id_x, max_val = st.session_state.height_max)
                
                # View and download data
                st.download_button(label="Download longitudinal profile", data=scanData_v2.to_csv().encode('utf-8'), file_name="lonProfile_" +str(id_x)+"_"+ str(idmin) +" to " + str(idmax)+ ".csv", mime = "csv")

    
    
