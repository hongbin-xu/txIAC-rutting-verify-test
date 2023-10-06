import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Authentication function
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True

@st.cache_data
def dataLoad(_conn, segID=None, idmin = None, idmax=None, mode = "1"):
    """
    mode1: select for each segment
    mode2: select for multiple segment
    creating 2d array of the height measurement
    """
    if mode =="1":
        data = conn.query('SELECT * from pathway_raw_fm365_sep13 WHERE segID =' + str(segID) +';')
    if mode =="2":
        data = conn.query('SELECT * from pathway_raw_fm365_sep13 WHERE id BETWEEN '+ str(idmin) +' AND ' + str(idmax)+';')
    tranStep = data["tranStep"].mean()
    lonStep = data["lonStep"].mean()
    dataArray = np.array([np.array(data["height"][i].split(b',')).astype("float") for i in range(data.shape[0])])
    
    return data, tranStep, lonStep, dataArray

@st.cache_data
def transExtrac(segData, id):
    # Extract transverse profile
    scanData = segData.loc[(segData["id"]==id), ["tranStep", "height"]].reset_index(drop=True)
    scanData_v1 = pd.DataFrame({"DIST":scanData["tranStep"][0]*np.arange(1536), "Height":np.array(scanData["height"][0].split(b",")).astype("float")})
    return scanData_v1

@st.cache_data
def surfPlot(data, dataArray, tranStep, lonStep):
    # hover information
    # id, segID, scanID, dataNum, DFO + mm, transverse mm
    customData= np.stack([data["segID"].values.reshape(dataArray.shape[0],-1).repeat(dataArray.shape[1], axis =1), # SegID 0
                        data["DFO"].values.reshape(dataArray.shape[0],-1).repeat(dataArray.shape[1], axis =1), # DFO 1
                        data["OFFSET"].values.reshape(dataArray.shape[0],-1).repeat(dataArray.shape[1], axis =1), # DFO offset 2
                        np.arange(dataArray.shape[1]).reshape(-1,dataArray.shape[1]).repeat(dataArray.shape[0], axis=0)*data["tranStep"].values.reshape(-1,1) # trans Distance 3
                        ], axis = -1)
    
    fig = px.imshow(dataArray, origin = "lower", 
                    labels = {"x": "Longitudinal profile id", "y": "Transverse profile id", "color": "Height (mm)"},
                    y = data["id"], #np.arange(dataArray.shape[0])*lonStep,
                    aspect="auto", 
                    height = 800)
    fig.update(data=[{'customdata': customData,
                      'hovertemplate': "<br>".join(["id: %{y:.0f}",
                                                    "segID: %{customdata[0]:.0f}",
                                                    "DFO: %{customdata[1]:.3f} mile",
                                                    "OFFSET: %{customdata[2]:.0f} mm",
                                                    "lonID: %{x:.0f}",
                                                    "transDist: %{customdata[3]:.0f} mm",
                                                    "Height: %{z} mm"])}])
    st.plotly_chart(fig, use_container_width=True, theme = None)

# Check authentication
if check_password():    
    # Page title
    st.set_page_config(page_title='IAC-Rutting Verification', layout="wide")
    conn = st.experimental_connection("mysql", type="sql")

    # sidebar
    #with st.sidebar:
    #    st.title("TxDOT Inter-Agency Contract")
    #    st.subheader("Rutting Measurement Verification")
    #    st.text("Maintenance Devision")
    #    st.text("Presented by Hongbin Xu and Jorge Prozzi")
    #    st.text("The University of Texas at Austin")
    
    # MySQL connection
    col1, col2 = st.columns(2, gap = "medium")
    with col1:
        with st.container():
            st.subheader("Suface")
            if st.checkbox('Data for individual segment', value = True):
                col11, col12 = st.columns(2)
                with col11:
                    segID = st.number_input("Segment ID", min_value=1, max_value=100, step= 1) # Segment ID
                    data, tranStep, lonStep, dataArray = dataLoad(_conn=conn, segID=segID, mode = "1") # load data
                with col12:
                    id_ = st.number_input("Transverse profile id", min_value=(segID-1)*900+1, max_value=segID*900, step = 1)
            else: 
                col11, col12 = st.columns(2)
                st.write('Data for multiple segments (selection of excessive data may leads to slow processing)')
                with col11:
                    idmin = st.number_input("id start", min_value=1, max_value=90000-50, value = 1, step= 1)
                    idmax = st.number_input("id end", min_value=idmin, max_value=min(90000, idmin + 1799), value = idmin+50, step= 1)
                    # Load data
                    data, tranStep, lonStep, dataArray = dataLoad(_conn=conn, idmin= idmin, idmax=idmax, mode ="2")
                with col12:
                    id_ = st.number_input("Transverse profile id", min_value=idmin, max_value=idmax, step = 1)
                    segID = id_//900+1
            st.write(str(data["ROUTE_NAME"][0])+ ", DFO: "+str(data["DFO"].min())+ "~"+ str(data["DFO"].max()))
            # plot surface
            with st.container():
                surfPlot(data=data, dataArray=dataArray, tranStep=tranStep, lonStep=lonStep)

    with col2:
        with st.container():
            st.subheader("Transverse Profile")

            # Extract transverse profile
            scanData_v1 = transExtrac(segData = data, id=id_)
            
            # Plot transverse profile
            fig = px.line(scanData_v1, x="DIST", y="Height", labels = {"DIST": "Transverse Distance (mm)", "Height": "Height (mm}"}, template = "plotly_dark")
            st.plotly_chart(fig)

            # View and download data
            st.download_button(label="Download profile", data=scanData_v1.to_csv().encode('utf-8'), file_name="transProfile_seg_" +str(segID)+"_scan_"+str(id_)+".csv", mime = "csv")
            if st.checkbox('Show raw transverse profile data'):
                st.write(scanData_v1)
        
    
    
    
