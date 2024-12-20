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

def calculate_cbm(length, width, height, quantity):
    return (length * width * height * quantity) / 1e9  # mm³을 m³으로 변환

def add_box(fig, vertices, color, name):
    # Mesh3d를 사용하여 박스의 4면을 색칠
    I = [0, 0, 0, 1, 1, 2, 3]
    J = [1, 3, 4, 2, 4, 5, 7]
    K = [3, 4, 5, 4, 5, 6, 6]
    
    fig.add_trace(go.Mesh3d(
        x=vertices[:, 0],
        y=vertices[:, 1],
        z=vertices[:, 2],
        i=I,
        j=J,
        k=K,
        color=color,
        opacity=0.9,
        name=name,
        showscale=False
    ))

    # 외곽선 추가 (Scatter3d)
    lines = [
        [0, 1], [1, 2], [2, 3], [3, 0],  # 바닥면
        [4, 5], [5, 6], [6, 7], [7, 4],  # 윗면
        [0, 4], [1, 5], [2, 6], [3, 7]   # 세로선
    ]

    for line in lines:
        fig.add_trace(go.Scatter3d(
            x=[vertices[line[0]][0], vertices[line[1]][0]],
            y=[vertices[line[0]][1], vertices[line[1]][1]],
            z=[vertices[line[0]][2], vertices[line[1]][2]],
            mode='lines',
            line=dict(color='black', width=2),
            showlegend=False
        ))

def draw_container(container_dim, boxes, container_type):
    fig = go.Figure()

    # 컨테이너 치수 및 CBM 계산
    cx, cy, cz = container_dim['length'], container_dim['width'], container_dim['height']
    container_cbm = (cx / 1000) * (cy / 1000) * (cz / 1000)  # mm³을 m³으로 변환

    # 컨테이너의 꼭짓점 정의
    container_vertices = np.array([
        [0, 0, 0],
        [cx, 0, 0],
        [cx, cy, 0],
        [0, cy, 0],
        [0, 0, cz],
        [cx, 0, cz],
        [cx, cy, cz],
        [0, cy, cz]
    ])

    # 컨테이너 그리기 (투명한 회색 박스)
    add_box(fig, container_vertices, 'lightgrey', 'Container')

    # 박스 배치 초기 위치
    current_x, current_y, current_z = 0, 0, 0
    used_cbm = 0
    total_loaded_boxes = 0

    # 제품별 고유 색상 목록 (더 많은 색상을 원할 경우 확장 가능)
    colors = ['yellow', 'cyan', 'magenta', 'lime', 'pink', 'teal', 'lavender', 'brown']
    color_idx = 0

    product_report = []

    for i, (bx, by, bz, cartons, per_carton, name) in enumerate(boxes):
        box_count = 0
        total_products = 0
        for _ in range(cartons):
            # 공간 초과 시 다음 행으로 이동
            if current_x + bx > cx:
                current_x = 0
                current_y += by

            # 공간 초과 시 다음 층으로 이동
            if current_y + by > cy:
                current_y = 0
                current_z += bz

            # 공간 초과 시 더 이상 배치 불가
            if current_z + bz > cz:
                st.warning(f"⚠️ 컨테이너에 더 이상 {name} 제품을 배치할 공간이 없습니다.")
                break

            # 박스의 꼭짓점 정의
            box_vertices = np.array([
                [current_x, current_y, current_z],
                [current_x + bx, current_y, current_z],
                [current_x + bx, current_y + by, current_z],
                [current_x, current_y + by, current_z],
                [current_x, current_y, current_z + bz],
                [current_x + bx, current_y, current_z + bz],
                [current_x + bx, current_y + by, current_z + bz],
                [current_x, current_y + by, current_z + bz]
            ])

            # 박스 그리기
            add_box(fig, box_vertices, colors[color_idx % len(colors)], name)
            used_cbm += calculate_cbm(bx, by, bz, 1)
            total_loaded_boxes += 1
            box_count += 1
            total_products += per_carton

            # 다음 박스의 x 좌표 업데이트
            current_x += bx

        # 제품별 CBM 및 전체 제품 수 계산
        product_cbm = calculate_cbm(bx, by, bz, box_count)
        product_report.append({
            "제품명": name,
            "선적된 박스 수": box_count,
            "전체 제품 수": total_products,
            "제품별 CBM": f"{product_cbm:.2f} m³"
        })

        color_idx += 1

    # 레이아웃 설정
    fig.update_layout(
        scene=dict(
            xaxis_title='Length (mm)',
            yaxis_title='Width (mm)',
            zaxis_title='Height (mm)',
            aspectmode='data',
            xaxis=dict(nticks=10, range=[0, cx + 1000]),
            yaxis=dict(nticks=10, range=[0, cy + 1000]),
            zaxis=dict(nticks=10, range=[0, cz + 1000]),
        ),
        margin=dict(r=10, l=10, b=10, t=50),
        title=f"{container_type} 컨테이너 선적 시뮬레이션"
    )

    st.plotly_chart(fig, use_container_width=True)

    # 결과 요약 출력
    st.subheader("선적 정보 요약")
    total_cbm_used = sum(float(report["제품별 CBM"].split()[0]) for report in product_report)
    remaining_cbm = container_cbm - total_cbm_used

    st.write(f"**사용된 CBM:** {total_cbm_used:.2f} m³")
    st.write(f"**남은 CBM:** {remaining_cbm:.2f} m³")

    # 추가 선적 가능 박스 수 계산
    st.write("**추가 선적 가능 박스 수 시뮬레이션:**")
    for report in product_report:
        if report["제품별 CBM"] == "0.00 m³":
            possible_boxes = 0
        else:
            # 단일 박스의 CBM
            single_cbm = float(report["제품별 CBM"].split()[0]) / report["선적된 박스 수"] if report["선적된 박스 수"] > 0 else 0
            possible_boxes = math.floor(remaining_cbm / single_cbm) if single_cbm > 0 else 0
        st.write(f"- **{report['제품명']}**: 추가로 {possible_boxes} 박스 선적 가능")

    st.write("\n")

    st.table(product_report)

    # PDF 생성 함수
    def create_pdf(container_type, container_dim, product_report, total_cbm_used, remaining_cbm):
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
    
        # 선적 정보 요약
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(50, 650, "선적 정보 요약:")
        pdf.setFont("Helvetica", 12)
        pdf.drawString(70, 630, f"사용된 CBM: {total_cbm_used:.2f} m³")
        pdf.drawString(70, 610, f"남은 CBM: {remaining_cbm:.2f} m³")
        pdf.drawString(70, 590, "제품별 선적 정보:")
        y = 570
        for report in product_report:
            pdf.drawString(90, y, f"- {report['제품명']}:")
            pdf.drawString(110, y - 20, f"선적된 박스 수: {report['선적된 박스 수']}")
            pdf.drawString(110, y - 40, f"전체 제품 수: {report['전체 제품 수']}")
            pdf.drawString(110, y - 60, f"제품별 CBM: {report['제품별 CBM']}")
            y -= 80
    
        pdf.showPage()
        pdf.save()
    
        buffer.seek(0)
        return buffer

    # PDF 다운로드 버튼
    if st.button("PDF로 출력"):
        if len(product_report) == 0:
            st.warning("시뮬레이션을 먼저 실행해주세요.")
        else:
            buffer = create_pdf(container_type, container_dim, product_report, total_cbm_used, remaining_cbm)
            st.download_button(
                label="PDF 다운로드",
                data=buffer,
                file_name="YNK_shipping_simulation.pdf",
                mime="application/pdf"
            )

    # Streamlit UI 설정
    st.set_page_config(page_title="혼적 컨테이너 선적 시뮬레이션", layout="wide")
    st.title("혼적 컨테이너 선적 시뮬레이션 (고급 3D)")

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
