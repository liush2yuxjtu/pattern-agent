// Source Human Studio calibration only. No reference data, loss or optimizer.
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';
import {pathToFileURL} from 'node:url';
const root=process.argv[2];
const data=JSON.parse(fs.readFileSync(path.join(root,'web/human-studio/assets/human.json'),'utf8'));
const {fitDimensions}=await import(pathToFileURL(path.join(root,'web/human-studio/body-engine.js')));
for await(const line of readline.createInterface({input:process.stdin,crlfDelay:Infinity})) {
  try {const request=JSON.parse(line),fit=fitDimensions(data,request.dimensions,request.weights,40);
    process.stdout.write(JSON.stringify({dimensions:fit.targets,weights:fit.weights,measurements:fit.measurements,maxError:fit.maxError})+'\n');
  } catch(error) {process.stdout.write(JSON.stringify({error:String(error)})+'\n');}
}
