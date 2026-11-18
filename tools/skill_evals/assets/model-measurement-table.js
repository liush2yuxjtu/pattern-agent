// Review-derived neutral geometry measurements, inside the native Output only.
function appendModelMeasurements(content,data){
  const measured=data.model_measurements;if(!measured)return;
  const labels={height:'站立身高',bust:'胸围',waist:'腰围',hips:'臀围',shoulders:'肩部标志点距离',upperArm:'上臂围',thigh:'大腿围',neck:'颈围',upperArmLength:'上臂标志点距离',forearmLength:'前臂标志点距离',thighLength:'大腿标志点距离',calf:'小腿围'};
  const section=document.createElement('section');section.className='og-measurements';
  const title=document.createElement('h3');title.textContent='人体模型实测尺寸（cm）';section.append(title);
  const note=document.createElement('p');note.textContent='从保存的 neutral.obj 顶点独立复量，主要输出为模型实测值；控制目标另列。围度按模型带尺路径、长度按标志点定义。模型受先验影响，尚非照片真人实测。';section.append(note);
  const table=document.createElement('table'),head=document.createElement('thead'),hr=document.createElement('tr');
  for(const name of ['项目','模型实测 cm','控制目标 cm','实测−目标 cm']){const th=document.createElement('th');th.textContent=name;hr.append(th);}head.append(hr);table.append(head);
  const body=document.createElement('tbody');
  for(const row of measured.measurements){const tr=document.createElement('tr');tr.dataset.measurement=row.name;
    const value=row.value_cm,target=row.body_parameter_target_cm,delta=row.input_target_delta_cm;
    for(const text of [labels[row.name]||row.label,value.toFixed(4),target===null?'未知':target.toFixed(2),delta===null?'未知':Math.abs(delta)<.0001?delta.toExponential(2):delta.toFixed(4)]){const td=document.createElement('td');td.textContent=text;tr.append(td);}body.append(tr);
  }table.append(body);section.append(table);
  const links=document.createElement('p');
  for(const [label,href]of [['下载模型实测 JSON',measured.json_href],['下载模型实测 CSV',measured.csv_href]]){const a=document.createElement('a');a.textContent=label;a.href=href;a.download='';links.append(a,document.createTextNode(' · '));}
  const fingerprint=document.createElement('p');fingerprint.textContent='测量网格 SHA256：'+measured.model_fingerprints.neutral_mesh_sha256;section.append(links,fingerprint);content.append(section);
}
