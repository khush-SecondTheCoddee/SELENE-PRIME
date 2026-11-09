"""Reproducible Apollo 11 / real LOLA / DE421 research case."""
from __future__ import annotations
import hashlib, json, math, random, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import spiceypy as spice
from selene_prime.apparent.positions import ApparentPositionService
from selene_prime.geometry.vectors import Vector3
from selene_prime.kernels.manifest import KernelManifest
from selene_prime.kernels.session import AberrationCorrection, KernelSession
from selene_prime.radiometry.disk import SolarDiskConfig, integrate_solar_disk
from selene_prime.terrain.horizon import HorizonConfig, TerrainHorizonEngine
from selene_prime.terrain.pds3_lola import LolaGdrProduct

def file_sha256(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""): digest.update(block)
    return digest.hexdigest()

def unit(v):
    n=math.sqrt(sum(x*x for x in v)); return tuple(x/n for x in v)

def local_angles(v,lat,lon):
    bases=((-math.sin(lon),math.cos(lon),0.0),
           (-math.sin(lat)*math.cos(lon),-math.sin(lat)*math.sin(lon),math.cos(lat)),
           (math.cos(lat)*math.cos(lon),math.cos(lat)*math.sin(lon),math.sin(lat)))
    e,n,u=(sum(v[i]*b[i] for i in range(3)) for b in bases)
    return math.atan2(e,n)%(2*math.pi), math.atan2(u,math.hypot(e,n))

def manual_bilinear(grid,lat,lon):
    row,col=grid.geometry.fractional_index(lat,lon)
    r0,c0=math.floor(row),math.floor(col); r1=min(r0+1,grid.geometry.rows-1); c1=(c0+1)%grid.geometry.columns
    fr,fc=row-r0,col-math.floor(col)
    samples=[grid.source.elevation(r0,c0),grid.source.elevation(r0,c1),grid.source.elevation(r1,c0),grid.source.elevation(r1,c1)]
    if any(x is None for x in samples): raise ValueError("NoData in independent bilinear reference stencil")
    a,b,c,d=map(float,samples)
    return a*(1-fr)*(1-fc)+b*(1-fr)*fc+c*fr*(1-fc)+d*fr*fc

def overlap_fraction(r1,r2,d):
    if d>=r1+r2: return 0.0
    if d<=abs(r2-r1): return min(1.0,(r2/r1)**2)
    a=math.acos(max(-1.0,min(1.0,(d*d+r1*r1-r2*r2)/(2*d*r1))))
    b=math.acos(max(-1.0,min(1.0,(d*d+r2*r2-r1*r1)/(2*d*r2))))
    area=r1*r1*a+r2*r2*b-.5*math.sqrt(max(0.0,(-d+r1+r2)*(d+r1-r2)*(d-r1+r2)*(d+r1+r2)))
    return area/(math.pi*r1*r1)

def independent_bisection(target,reception,observer,low_seconds=2000.0):
    c=299792.458
    def residual(et):
        state,_=spice.spkezr(target,et,"J2000","NONE","SOLAR SYSTEM BARYCENTER")
        d=math.sqrt(sum((state[i]-observer[i])**2 for i in range(3)))
        return et+d/c-reception
    lo,hi=reception-low_seconds,reception; flo,fhi=residual(lo),residual(hi)
    if flo*fhi>=0: raise RuntimeError(f"bisection interval does not bracket {target} light-time root")
    for _ in range(100):
        mid=(lo+hi)/2; fm=residual(mid)
        if abs(fm)<1e-10 or hi-lo<1e-9: lo=hi=mid; break
        if flo*fm<=0: hi,fhi=mid,fm
        else: lo,flo=mid,fm
    et=(lo+hi)/2; state,_=spice.spkezr(target,et,"J2000","NONE","SOLAR SYSTEM BARYCENTER")
    return tuple(state[i]-observer[i] for i in range(3)), reception-et

def main():
    out_dir=ROOT/"reports"/"real_case"; out_dir.mkdir(parents=True,exist_ok=True)
    expected_img="a511e40d7a3ea3275945b4da2a1df377133264fab0be94b7434b1cf8907254cb"
    utc="2024-04-08T18:00:00 UTC"
    manifest=KernelManifest.load(ROOT/"config/research_kernels_de421.json")
    mirror=ROOT/"data/real/lola_gdr/LDEM_16_mirror.IMG"
    mirror_sha=file_sha256(mirror)
    script_sha=file_sha256(Path(__file__))
    manifest_sha=file_sha256(ROOT/"config/research_kernels_de421.json")
    report={"case":"Apollo 11 / LDEM_16 / DE421","epoch_utc":utc,
            "status":"computed; interpretation limited to documented models and inputs","metrics":{}}
    with LolaGdrProduct.open(ROOT/"data/real/lola_gdr/ldem_16.lbl",expected_image_sha256=expected_img) as product:
      grid=product.grid
      with KernelSession(manifest) as session:
        et=float(spice.str2et(utc))  # LSK is loaded by the context before UTC conversion.
        sun_cov=session.validate_state_query("SUN","SOLAR SYSTEM BARYCENTER",et,"J2000",AberrationCorrection.NONE)
        earth_cov=session.validate_state_query("EARTH","SOLAR SYSTEM BARYCENTER",et,"J2000",AberrationCorrection.NONE)
        slat,slon=map(math.radians,(0.67409,23.47298)); radius=grid.reference_radius_m
        p0=Vector3(radius/1000*math.cos(slat)*math.cos(slon),radius/1000*math.cos(slat)*math.sin(slon),radius/1000*math.sin(slat),"km")
        pm=session.transform_vector(p0,"IAU_MOON","MOON_ME_DE421",et)
        lat=math.atan2(pm.z,math.hypot(pm.x,pm.y)); lon=math.atan2(pm.y,pm.x)
        height=grid.elevation_m(math.degrees(lat),math.degrees(lon))
        if height is None or not math.isfinite(height): raise RuntimeError("Station lies on LOLA NoData")
        station=Vector3((radius+height)/1000*math.cos(lat)*math.cos(lon),(radius+height)/1000*math.cos(lat)*math.sin(lon),(radius+height)/1000*math.sin(lat),"km")
        pb=session.transform_vector(pm,"MOON_ME_DE421","IAU_MOON",et)
        frame_err=math.sqrt(sum((a-b)**2 for a,b in zip((pb.x,pb.y,pb.z),(p0.x,p0.y,p0.z))))*1000
        bilib=manual_bilinear(grid,math.degrees(lat),math.degrees(lon)); bilib_actual=grid.elevation_m(math.degrees(lat),math.degrees(lon))
        service=ApparentPositionService(session)
        sun=service.position("SUN",et,station,"MOON_ME_DE421",target_radius_km=695700.0)
        earth=service.position("EARTH",et,station,"MOON_ME_DE421",target_radius_km=6378.1366)
        rot=session.frame_rotation("J2000","MOON_ME_DE421",et)
        sv=rot.apply(sun.position_km); ev=rot.apply(earth.position_km)
        saz,sel=local_angles((sv.x,sv.y,sv.z),lat,lon); eaz,eel=local_angles((ev.x,ev.y,ev.z),lat,lon)
        moon=spice.spkezr("MOON",et,"J2000","NONE","SOLAR SYSTEM BARYCENTER")[0]
        sitej=session.frame_rotation("MOON_ME_DE421","J2000",et).apply(station)
        site=(sitej.x,sitej.y,sitej.z); observer=tuple(moon[i]+site[i] for i in range(3))
        refvec,reflt=independent_bisection("SUN",et,observer)
        a=unit((sun.position_km.x,sun.position_km.y,sun.position_km.z)); b=unit(refvec)
        direction_err=math.acos(max(-1.0,min(1.0,sum(a[i]*b[i] for i in range(3)))))
        engine=TerrainHorizonEngine(); horizons=[]
        for frac in (.5,.25,.125):
            hres=engine.horizon(grid,math.degrees(lat),math.degrees(lon),saz,HorizonConfig(50000,frac))
            horizons.append({"step_fraction_pixel":frac,"horizon_elevation_deg":math.degrees(hres.elevation_rad),
              "range_at_maximum_m":hres.range_at_maximum_m,"samples":hres.samples,"maximum_step_m":hres.maximum_step_m})
        profile=[engine.horizon(grid,math.degrees(lat),math.degrees(lon),math.radians(i),HorizonConfig(50000,.5)).elevation_rad for i in range(360)]
        def horizon_at(az):
            x=(az%(2*math.pi))*180/math.pi; i=math.floor(x)%360; f=x-math.floor(x)
            return profile[i]*(1-f)+profile[(i+1)%360]*f
        sr=math.asin(695700/sun.distance_km); er=math.asin(6378.1366/earth.distance_km)
        sep=math.acos(max(-1.0,min(1.0,math.sin(sel)*math.sin(eel)+math.cos(sel)*math.cos(eel)*math.cos(saz-eaz))))
        analytic=overlap_fraction(sr,er,sep); disks=[]
        for n in (32,64,128):
            res=integrate_solar_disk(solar_angular_radius_rad=sr,solar_azimuth_rad=saz,solar_elevation_rad=sel,
              config=SolarDiskConfig(1361.0,sun.distance_km/149597870.7,0.0,"uniform disk (u=0), no spectral passband","IAU nominal TSI 1361 W/m^2; NASA SORCE/TIM basis",n),
              earth_angular_radius_rad=er,earth_azimuth_rad=eaz,earth_elevation_rad=eel,horizon_elevation=horizon_at)
            disks.append({"subdivisions":n,"visible_fraction":res.visible_fraction,"earth_occluded_fraction":res.earth_occluded_fraction,
              "terrain_occluded_fraction":res.terrain_occluded_fraction,"combined_occluded_fraction":res.combined_occluded_fraction,
              "direct_normal_W_m2_illustrative_only":res.direct_normal_w_m2,"sample_count":res.sample_count})
        rng=random.Random(20260408); half=.5/grid.geometry.pixels_per_degree; jitter=[]
        for _ in range(32):
            jl=math.degrees(lat)+(2*rng.random()-1)*half; jo=math.degrees(lon)+(2*rng.random()-1)*half
            jitter.append(math.degrees(engine.horizon(grid,jl,jo,saz,HorizonConfig(50000,.5)).elevation_rad))
        report["reproducibility"]={"run_script_sha256":script_sha,"kernel_manifest_sha256":manifest_sha}
        report["epoch_et_tdb_seconds_past_j2000"]=et
        report["data"]={"product_id":product.metadata.product_id,"dataset_id":product.provenance.data_set_id,"pds3":True,"dimensions_rows_columns":[product.metadata.rows,product.metadata.columns],
          "native_frame":product.metadata.native_frame,"latitude_type":product.metadata.latitude_type,"longitude_direction":product.metadata.longitude_direction,
          "pixel_registration":product.metadata.pixel_registration,"reference_radius_m":radius,"pixels_per_degree":product.metadata.pixels_per_degree,
          "image_sha256":product.provenance.image_sha256,"independent_official_mirror_sha256":mirror_sha,
          "official_host_byte_match":mirror_sha==product.provenance.image_sha256,
          "official_archive_url":"https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/LDEM_16.IMG",
          "second_official_host_url":"https://imbrium.mit.edu/DATA/LOLA_GDR/CYLINDRICAL/IMG/LDEM_16.IMG","label_sha256":product.provenance.label_sha256,"label_external_checksum_verified":product.provenance.label_sha256_verified}
        report["kernels"]=[{"path":k.path,"sha256":k.sha256,"kind":k.kind.value,"role":k.role.value,"source":k.source,"size_bytes":k.size_bytes} for k in session.loaded_kernels]
        report["station"]={"name":"Apollo 11 / Tranquility Base","source_coordinates_IAU_ME_deg":{"latitude":.67409,"east_longitude":23.47298},
          "transformed_dem_coordinates_MOON_ME_DE421_deg":{"planetocentric_latitude":math.degrees(lat),"east_longitude":math.degrees(lon)},
          "sample_height_m":height,"height_definition":"LOLA DN*0.5 m relative to the 1,737,400 m reference sphere",
          "frame_transform":"IAU_MOON to MOON_ME_DE421 using loaded DE421 FK/PCK at epoch","roundtrip_error_m":frame_err}
        report["ephemeris"]={"queries":{"SUN relative SSB ET":sun_cov.et_tdb_seconds_past_j2000,"EARTH relative SSB ET":earth_cov.et_tdb_seconds_past_j2000},
          "method":"Topocentric station state; iterated one-way LT; no stellar aberration",
          "solar_irradiance_reference":{"value_W_m2_at_1_au":1361.0,"kind":"IAU nominal total solar irradiance, bolometric","source":"https://earth.gsfc.nasa.gov/climate/projects/solar-irradiance/science","uncertainty_and_solar_cycle_variation_not_propagated":True},
          "sun":{"distance_km":sun.distance_km,"light_time_s":sun.light_time_seconds,"angular_radius_deg":math.degrees(sr),"azimuth_deg":math.degrees(saz),"elevation_deg":math.degrees(sel)},
          "earth":{"distance_km":earth.distance_km,"light_time_s":earth.light_time_seconds,"angular_radius_deg":math.degrees(er),"azimuth_deg":math.degrees(eaz),"elevation_deg":math.degrees(eel)}}
        report["metrics"]={"manual_bilinear_height_m":bilib,"library_height_m":bilib_actual,"bilinear_abs_difference_m":abs(bilib-bilib_actual),
          "bisection_direction_difference_arcsec":math.degrees(direction_err)*3600,
          "direction_difference_fraction_solar_radius":direction_err/sr,"bisection_light_time_s":reflt,"horizon_refinement":horizons,
          "solar_disk_quadrature":disks,"successive_disk_visibility_absolute_changes":[abs(disks[i]["visible_fraction"]-disks[i-1]["visible_fraction"]) for i in range(1,len(disks))],
          "analytical_euclidean_circle_overlap_fraction":analytic,
          "analytic_vs_quadrature_earth_occultation_abs_error":abs(disks[-1]["earth_occluded_fraction"]-analytic),
          "horizon_location_jitter_32_min_max_deg":[min(jitter),max(jitter)],"horizon_location_jitter_range_deg":max(jitter)-min(jitter),
          "horizon_successive_absolute_changes_deg":[abs(horizons[i]["horizon_elevation_deg"]-horizons[i-1]["horizon_elevation_deg"]) for i in range(1,len(horizons))],
          "jitter_seed":20260408,"per_coordinate_half_pixel_jitter_deg":half}
        earth_quad_error=abs(disks[-1]["earth_occluded_fraction"]-analytic)
        report["validation"]={"benchmarks":[
          {"metric":"apparent Sun direction, light-time iteration versus independent bisection",
           "reference":"separate bisection root over direct SPICE geometric SSB states; same DE421 kernel",
           "actual_absolute_error_arcsec":math.degrees(direction_err)*3600,
           "relative_error_to_solar_angular_radius":direction_err/sr,
           "user_requested_threshold_fraction_of_solar_radius":0.01,
           "pass":direction_err/sr<0.01,"independent_ephemeris_truth":False},
          {"metric":"Earth occultation fraction, disk quadrature versus analytical circle overlap",
           "reference_value_fraction":analytic,"actual_value_fraction":disks[-1]["earth_occluded_fraction"],
           "absolute_error_fraction":earth_quad_error,
           "relative_error":None if analytic==0 else earth_quad_error/analytic,
           "absolute_tolerance_fraction":0.01,"pass":earth_quad_error<0.01,
           "note":"A zero-overlap reference uses absolute error only."},
          {"metric":"LOLA bilinear interpolation at transformed station coordinate",
           "reference_value_m":bilib,"actual_value_m":bilib_actual,
           "absolute_difference_m":abs(bilib-bilib_actual),"status":"algorithm check using direct four-sample formula; not an external terrain-accuracy validation"}],
          "scope":"A pass applies only to that metric and case; no global <1% scientific accuracy claim."}
        report["limitations"]=["PDS supplies no detached-label checksum; image independently matched a byte-for-byte second official host copy.",
          "LOLA grid is kilometre-scale and label gives no formal vertical covariance; location jitter is sensitivity, not confidence interval.",
          "Earth is opaque sphere; atmosphere ignored.","Uniform solar disk uses no limb-darkening model; irradiance uses nominal bolometric 1361 W/m^2 and omits solar-cycle/input uncertainty.",
          "Apparent-position reference changes light-time algorithm but shares DE421 ephemeris, so is not independent ephemeris truth.",
          "No NASA/CLPS qualification, certification, or Space Apps outcome is asserted."]
    out=out_dir/"apollo11_2024-04-08T180000Z.json"
    out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(out.relative_to(ROOT)); print(json.dumps(report["metrics"],indent=2,sort_keys=True))

if __name__=="__main__": main()
