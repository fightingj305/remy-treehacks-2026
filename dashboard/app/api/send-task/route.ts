import { NextRequest, NextResponse } from 'next/server';
import net from 'net';

export async function POST(req: NextRequest) {
  const { recipeTaskQueue, host, port } = await req.json();

  if (!recipeTaskQueue || !host || !port) {
    return NextResponse.json(
      { error: 'Missing recipeTaskQueue, host, or port' },
      { status: 400 }
    );
  }

  return new Promise<NextResponse>((resolve) => {
    const client = new net.Socket();
    const timeout = setTimeout(() => {
      client.destroy();
      resolve(NextResponse.json({ error: 'Connection timed out' }, { status: 504 }));
    }, 5000);

    client.connect(port, host, () => {
      const payload = JSON.stringify(recipeTaskQueue);
      const buf = Buffer.from(payload, 'utf-8');
      const header = Buffer.alloc(4);
      header.writeUInt32BE(buf.length);
      client.write(Buffer.concat([header, buf]));
      client.end();
    });

    client.on('close', () => {
      clearTimeout(timeout);
      resolve(NextResponse.json({ success: true }));
    });

    client.on('error', (err) => {
      clearTimeout(timeout);
      resolve(NextResponse.json({ error: err.message }, { status: 500 }));
    });
  });
}
