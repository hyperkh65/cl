import streamlit as st
import plotly.graph_objects as go
import numpy as np
import math
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# 컨테이너 정보 (단위: mm)
CONTAINERS = {
    "20ft": {"length": 5898, "width": 2352, "height": 2395},
    "40ft": {"length": 12021, "width": 2352, "height": 2395},
    "40ft HC": {"length": 12021, "width": 2352, "height": 2691},
}

def calculate_cartons(per_carton, order_qty):
    return math.ceil(order_qty / per_carton)

def draw_container(container_dim, boxes, container_type):
    fig = go.Figure()

    # 컨테이너 치수 및 CBM 계산
    cx, cy, cz = container_dim['length'], container_dim['width'], container_dim['height']
    container_cbm = (cx / 1000) * (cy / 1000) * (cz / 1000)

    # 컨테이너 그리기
    fig.add_trace(go.Mesh3d(
        x=[0, cx, cx, 0, 0, cx, cx, 0],
        y=[0, 0, cy, cy, 0, 0, cy, cy],
        z=[0, 0, 0, 0, cz, cz, cz, cz],
        i=[0, 0, 0, 1, 2, 3, 4, 5, 6, 7],
        j=[1, 2, 3, 2, 3, 0, 5, 6, 7, 4],
        k=[4, 5, 6, 6, 7, 7, 1, 2, 3, 3],
        color='lightgrey',
        opacity=0.5
    ))

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("PDF로 출력")
    if st.button("PDF로 출력"):
        create_pdf(container_type, container_dim, boxes, container_cbm)

def create_pdf(container_type, container_dim, boxes, container_cbm):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle("YNK 선적 시뮬레이션")

    # 타이틀
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(200, 750, "YNK 선적 시뮬레이션 보고서")

    # 컨테이너 정보
    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, 720, f"컨테이너 타입: {container_type}")
    pdf.drawString(50, 700, f"내부 치수: {container_dim['length']} x {container_dim['width']} x {container_dim['height']} mm")
    pdf.drawString(50, 680, f"총 CBM: {container_cbm:.2f} m³")

    # 제품 정보
    y = 640
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "제품 정보:")
    pdf.setFont("Helvetica", 12)
    y -= 20

    for i, (length, width, height, cartons, per_carton, name) in enumerate(boxes):
        pdf.drawString(50, y, f"{i + 1}. 제품명: {name}")
        pdf.drawString(70, y - 20, f"크기: {length} x {width} x {height} mm")
        pdf.drawString(70, y - 40, f"카톤당 수량: {per_carton}")
        pdf.drawString(70, y - 60, f"총 카톤 수: {cartons}")
        y -= 80

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    st.download_button(
        label="PDF 다운로드",
        data=buffer,
        file_name="YNK_shipping_simulation.pdf",
        mime="application/pdf"
    )

# Streamlit UI 설정
st.set_page_config(page_title="YNK 선적 시뮬레이션", layout="wide")
st.title("YNK 선적 시뮬레이션")

# 사이드바 옵션창 생성
with st.sidebar:
    st.header("옵션 창")

    # 컨테이너 선택
    container_type = st.selectbox("컨테이너 사이즈 선택", list(CONTAINERS.keys()))
    container_dim = CONTAINERS[container_type]

    # 제품 수량 선택
    num_products = st.number_input("선적할 제품 종류 수", min_value=1, max_value=5, step=1)

    products = []
    for i in range(int(num_products)):
        with st.expander(f"제품 {i + 1} 설정", expanded=True):
            name = st.text_input(f"제품 {i + 1} 이름", f"Product {i + 1}")
            length = st.number_input(f"제품 {i + 1} 길이 (mm)", min_value=1, key=f'length_{i}')
            width = st.number_input(f"제품 {i + 1} 너비 (mm)", min_value=1, key=f'width_{i}')
            height = st.number_input(f"제품 {i + 1} 높이 (mm)", min_value=1, key=f'height_{i}')
            per_carton = st.number_input(f"제품 {i + 1} 카톤당 수량", min_value=1, key=f'per_carton_{i}')
            order_qty = st.number_input(f"제품 {i + 1} 발주 수량", min_value=1, key=f'order_qty_{i}')
            cartons = calculate_cartons(per_carton, order_qty)
            st.write(f"**총 카톤 수:** {cartons}")
            products.append((length, width, height, cartons, per_carton, name))

# 시뮬레이션 버튼
if st.button("시뮬레이션 시작"):
    draw_container(container_dim, products, container_type)
