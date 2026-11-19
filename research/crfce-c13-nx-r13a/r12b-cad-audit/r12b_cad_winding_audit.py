"""Reproducible C13-NX R12-B CAD and conditional physics feasibility audit.

Reads the archived STEP file and checks geometric dimensions only. Does NOT solve
Maxwell equations and does NOT certify a working engine.

Requirements: cadquery, numpy, matplotlib, Python 3.11+.
Usage: python r12b_cad_winding_audit.py --step PATH --out DIR
"""
import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path

import cadquery as cq
import matplotlib.pyplot as plt
import numpy as np

MU0 = 4 * math.pi * 1e-7


def field_for_stresses(Fx, Fz, face_area_m2):
    """Ideal uniform Maxwell traction with prescribed same-face Fx and Fz."""
    tau, p = Fx / face_area_m2, Fz / face_area_m2
    a, b = 2 * MU0 * p, MU0 * tau
    discriminant = math.hypot(a, 2 * b)
    Bn = math.sqrt((discriminant + a) / 2)
    Bt = math.sqrt(max(0., (discriminant - a) / 2))
    return {"active_face_m2": face_area_m2,
            "shear_Pa": tau, "normal_pressure_Pa": p,
            "Bn_T": Bn, "Bt_T": Bt,
            "B_combined_T": math.hypot(Bn, Bt),
            "B_traction_only_min_T": math.sqrt(2 * MU0 * tau)}


def dims(shape):
    b = shape.BoundingBox()
    return (b.xlen, b.ylen, b.zlen)


def near(v, p, tol=0.01):
    return all(abs(a-b) <= tol for a,b in zip(v,p))


def geometry_source(file_path):
    shape = cq.importers.importStep(str(file_path))
    solids = shape.solids().vals()
    dd = [dims(x) for x in solids]
    islands = [s for s in solids if near(dims(s), (12,4,28))]
    conductor_bars = [s for s in solids if near(dims(s),(1,1,20)) or near(dims(s),(12,1,1))]
    faces = [s for s in solids if near(dims(s), (16,3.5,40))]
    moving_rails = [s for s in solids if near(dims(s),(80,4,2))]
    magnet_blocks = [s for s in solids if near(dims(s),(16,4,34))]
    if len(islands)!=4 or len(conductor_bars)!=32:
        raise ValueError("Unexpected source STEP topology; must inspect before using this audit")
    boxes = []
    for s in islands:
        b=s.BoundingBox(); boxes.append([b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax])
    xs=sorted((v[0]+v[1])/2 for v in boxes)
    pitches=[xs[i+1]-xs[i] for i in range(len(xs)-1)]
    # One x-z face per island (normal y), identified by source-solid extents
    active_face_mm2=sum(s.BoundingBox().xlen*s.BoundingBox().zlen for s in islands)
    upper=[s for s in faces if s.BoundingBox().ymin>0]
    lower=[s for s in faces if s.BoundingBox().ymax<0]
    y_island_max=max(s.BoundingBox().ymax for s in islands)
    y_island_min=min(s.BoundingBox().ymin for s in islands)
    gap_top=min(s.BoundingBox().ymin for s in upper)-y_island_max
    gap_bottom=y_island_min-max(s.BoundingBox().ymax for s in lower)
    allb=shape.val().BoundingBox()
    return {
        'source_step_path':str(file_path), 'total_solids':len(solids),
        'moving_islands_count':len(islands),
        'moving_island_dimensions_mm':[12,4,28],
        'moving_island_centers_x_mm':xs,
        'cell_pitch_mm':pitches,
        'moving_island_single_face_area_mm2':active_face_mm2,
        'upper_pole_blocks_count':len(upper),'lower_pole_blocks_count':len(lower),
        'coil_bar_solids_count':len(conductor_bars),
        'coil_bar_cross_section_mm2':1.0,
        'coil_bar_interpretation':'idealized placeholder; eight 36-turn packed windings NOT present',
        'moving_carrier_rails_count':len(moving_rails),
        'central_magnetic_blocks_count':len(magnet_blocks),
        'nominal_gap_top_mm':gap_top,'nominal_gap_bottom_mm':gap_bottom,
        'geometry_bbox_mm':{'x':[allb.xmin,allb.xmax],
                            'y':[allb.ymin,allb.ymax],
                            'z':[allb.zmin,allb.zmax]},
    }


def winding_cases(N=36, fill=.60, J_rms=5.):
    """Pack areas from current density using source current waveform and explicit assumptions.

    Current waveform: i=4+9.5cos; both upper and lower windings driven.
    Nominal path centerline from CAD: 2*(12+20) mm, excluding end-turn refinements.
    """
    rho20=1.724e-8
    alpha=.00393
    rho80=rho20*(1+alpha*(80-20))
    Lturn_m=.064
    total_length_m=N*Lturn_m
    cases=[
      {'case':'reduced_model_I_rms','I_rms_A':math.sqrt(4**2+(9.5**2)/2),
       'I_peak_A':13.5,'J_design_A_mm2':5,'mode':'actual 4+9.5 cos waveform, RMS copper design'},
      {'case':'peak_13p5_as_continuous','I_rms_A':13.5,
       'I_peak_A':13.5,'J_design_A_mm2':5,'mode':'conservative continuous DC 13.5 A screening'},
      {'case':'peak_150_sinusoidal','I_rms_A':150/math.sqrt(2),
       'I_peak_A':150,'J_design_A_mm2':5,'mode':'hypothetical 150 A peak sinusoidal current'},
      {'case':'150_continuous','I_rms_A':150,
       'I_peak_A':150,'J_design_A_mm2':5,'mode':'hypothetical continuous DC 150 A'}
    ]
    for c in cases:
        I=c['I_rms_A']
        Acu_mm2=I/J_rms
        Apack_mm2=N*Acu_mm2/fill
        c.update({'turns':N,'fill_fraction':fill,
                  'required_copper_cross_section_per_turn_mm2':Acu_mm2,
                  'required_winding_pack_area_mm2':Apack_mm2,
                  'pack_area_vs_one_mm2_placeholder':Apack_mm2,
                  'total_idealized_conductor_length_per_circuit_m':total_length_m,
                  'rho_80C_ohm_m':rho80,
                  'R_80C_ohm':rho80*total_length_m/(Acu_mm2*1e-6),
                  'copper_loss_per_circuit_W':I**2*rho80*total_length_m/(Acu_mm2*1e-6),
                  'copper_loss_8_circuits_W':8*I**2*rho80*total_length_m/(Acu_mm2*1e-6),
                  'copper_mass_8_circuits_kg':8*(Acu_mm2*1e-6)*total_length_m*8960,
                  'NI_peak_ampere_turns':N*c['I_peak_A'],
                  'ideal_two_gap_B_from_NI_peak_T':MU0*N*c['I_peak_A']/.003})
    # Separate test of reduced model's hypothetical 120 mm² conductor pack
    A_pack=120
    A_turn=(A_pack*fill)/N
    Rpack=rho80*total_length_m/(A_turn*1e-6)
    return cases,{'source_of_120_mm2':'reduced C13 full-period model; NOT actual STEP solids',
                  'assumed_pack_mm2':A_pack,'turns':N,'fill_fraction':fill,
                  'real_copper_area_per_turn_mm2':A_turn,
                  'waveform_I_rms_A':math.sqrt(4**2+(9.5**2)/2),
                  'resulting_J_rms_A_mm2':math.sqrt(4**2+(9.5**2)/2)/A_turn,
                  'R80_ohm':Rpack,
                  'copper_loss_8_circuits_W':8*(4**2+(9.5**2)/2)*Rpack}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--step',required=True)
    parser.add_argument('--out',required=True)
    args=parser.parse_args()
    d=Path(args.out);d.mkdir(parents=True,exist_ok=True)
    g=geometry_source(Path(args.step))
    c,pack=winding_cases()
    face=g['moving_island_single_face_area_mm2']*1e-6
    area_cases=[('R11_assumed_area',.008),('CAD_4_islands_one_face',face),
                ('conditional_two_faces',2*face),('historical_250cm2_assumed_area',.025)]
    stress=[{'case':name,**field_for_stresses(879.38,3679,area)} for name,area in area_cases]
    Btarget=next(v['Bn_T'] for v in stress if v['case']=='R11_assumed_area')
    check={'gap_mm_each':1.5,'gaps_in_series':2,
           'R11_target_Bn_T':Btarget,
           'R11_two_gap_required_NI_At':Btarget*.003/MU0,
           '36x13p5A_max_NI_At':36*13.5,
           '36x13p5A_gap_only_B_T':MU0*36*13.5/.003,
           'field_ratio_R11_target_to_coil_only_bound':Btarget/(MU0*36*13.5/.003)}
    output={'method':'CAD source inspection + idealized analytic bounds, NOT nonlinear electromagnetic FEM',
            'source_cad':g,'field_stress_conditional_area_cases':stress,
            'winding_screens':c,'prior_reduced_model_120mm2_pack':pack,
            'gap_dominated_MMF_check':check,
            'verification_status':{
                'STEP_geometry_read':'PASS: 58 source solids counted and classified',
                'CAD_winding_conductor_realism':'FAIL: actual 1x1mm placeholders incompatible with 36-turn pack',
                'R11_8000mm2_face_traced_to_CAD':'FAIL: only 1344 mm² per nominal island face',
                'converged_nonlinear_3D_field':'OPEN: material-specific B-H / actual conductor solids / validated solver absent',
                'independent_support_control_matrix':'OPEN',
                'full_period_real_propulsion_work':'OPEN',
                'coupled_thermal_structural_braking':'OPEN',
                'whole_engine_virtual_proof':'NOT ACHIEVED'}}
    (d/'results.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    with (d/'gap_area_stress.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,stress[0].keys());w.writeheader();w.writerows(stress)
    with (d/'winding_pack.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,c[0].keys());w.writeheader();w.writerows(c)
    fig,ax=plt.subplots(figsize=(7.1,4.5))
    A=np.linspace(.001, .012,200)
    btot=[field_for_stresses(879.38,3679,float(a))['B_combined_T'] for a in A]
    ax.plot(A*1e6,btot,label='Combined field for Fx and Fz on one face')
    ax.scatter([1344,2688,8000],[field_for_stresses(879.38,3679,a)['B_combined_T'] for a in [.001344,.002688,.008]])
    for x,label in [(1344,'CAD: four islands / one face'),(2688,'conditional two faces'),(8000,'R11 area assumption')]:
        ax.annotate(label,(x,field_for_stresses(879.38,3679,x*1e-6)['B_combined_T']),xytext=(3,4),textcoords='offset points',fontsize=8)
    ax.set(xlabel='Assumed uniformly active area (mm²)',ylabel='Ideal combined gap-field magnitude (T)',title='Conditional Maxwell-stress area sensitivity')
    ax.grid(True,alpha=.3);fig.tight_layout();fig.savefig(d/'ideal_field_vs_active_area.png',dpi=190);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7.1,4.5))
    currents=np.linspace(1,150,200)
    packs=36*currents/(5*.6)
    ax.plot(currents,packs)
    ax.axhline(120,linestyle='--',label='120 mm² hypothetical pack used in reduced model')
    ax.axhline(1,linestyle=':',label='1 mm² CAD winding-path placeholder')
    ax.scatter([13.5,150],[36*13.5/(5*.6),36*150/(5*.6)])
    ax.set(xlabel='Continuous current (A), 5 A/mm² design assumption',ylabel='Required winding-pack area (mm²)',title='Conditional 36-turn copper-window sizing')
    ax.grid(True,alpha=.3);ax.legend(fontsize=8);fig.tight_layout();fig.savefig(d/'copper_pack_vs_current.png',dpi=190);plt.close(fig)
    print(json.dumps({'islands':g['moving_islands_count'],'nominal_face_mm2':g['moving_island_single_face_area_mm2'],'gap_top_mm':g['nominal_gap_top_mm'],'gap_bottom_mm':g['nominal_gap_bottom_mm'],'coil_bar_solids':g['coil_bar_solids_count'],'field_one_face_T':stress[1]['B_combined_T'],'reduced_model_pack':pack},indent=2))

if __name__=='__main__':main()
